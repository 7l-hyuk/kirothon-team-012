"""사진 저장소 테스트. boto3 클라이언트는 가짜 객체로 바꾸고, S3에는 접속하지 않습니다."""

import io
import logging
import re
import uuid

import pytest
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from sqlmodel import Session

from app import db
from app import storage as storage_module
from app.config import get_settings
from app.errors import ApiError
from app.models import Analysis, Photo
from app.storage import LocalStorage, S3Storage, get_storage, storage_kind
from app.storage import s3 as s3_module
from tests.conftest import JPEG, count_rows
from tests.test_ai_assist import analyze, setup_reports, upload

KEY_RE = r"photos/\d{4}/\d{2}/[0-9a-f-]{36}\.jpg"


class FakeS3:
    """boto3 S3 클라이언트 대역. 호출 인자를 기록합니다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.objects: dict[tuple[str, str], bytes] = {}
        self.fail: dict[str, Exception] = {}

    def _record(self, name: str, **kwargs) -> None:
        self.calls.append((name, kwargs))
        if name in self.fail:
            raise self.fail[name]

    def put_object(self, **kwargs):
        self._record("put_object", **kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs):
        self._record("get_object", **kwargs)
        return {"Body": io.BytesIO(self.objects[(kwargs["Bucket"], kwargs["Key"])])}

    def generate_presigned_url(self, operation, Params, ExpiresIn):  # noqa: N803  (boto3 인자 이름 그대로)
        self._record("generate_presigned_url", operation=operation, Params=Params, ExpiresIn=ExpiresIn)
        return f"https://{Params['Bucket']}.s3.ap-northeast-2.amazonaws.com/{Params['Key']}?X-Amz-Expires={ExpiresIn}"

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def client_error(code: str = "AccessDenied") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "secret-bucket-detail"}}, "PutObject")


@pytest.fixture
def s3(monkeypatch) -> FakeS3:
    """S3_BUCKET을 설정하고, S3Storage가 가짜 클라이언트를 쓰게 합니다."""
    fake = FakeS3()
    monkeypatch.setenv("S3_BUCKET", "shingomate-photos")
    monkeypatch.setenv("PRESIGN_EXPIRES_SECONDS", "900")
    get_settings.cache_clear()
    storage_module._cache = None
    monkeypatch.setattr(s3_module, "make_client", lambda region: fake)
    return fake


# ---------------------------------------------------------------- S3Storage 단위
def test_s3_put_sends_bucket_key_body_and_no_acl():
    fake = FakeS3()
    S3Storage("b", "ap-northeast-2", 3600, client=fake).put("photos/2026/11/x.jpg", b"jpeg-bytes")
    assert fake.calls == [
        (
            "put_object",
            {"Bucket": "b", "Key": "photos/2026/11/x.jpg", "Body": b"jpeg-bytes", "ContentType": "image/jpeg"},
        )
    ]
    assert "ACL" not in fake.calls[0][1]


def test_s3_url_is_presigned_get_with_configured_expiry():
    fake = FakeS3()
    url = S3Storage("b", "ap-northeast-2", 900, client=fake).url("photos/2026/11/x.jpg", "pid")
    assert fake.calls == [
        (
            "generate_presigned_url",
            {"operation": "get_object", "Params": {"Bucket": "b", "Key": "photos/2026/11/x.jpg"}, "ExpiresIn": 900},
        )
    ]
    assert url.startswith("https://b.s3.ap-northeast-2.amazonaws.com/photos/2026/11/x.jpg")


def test_s3_get_reads_bytes():
    fake = FakeS3()
    storage = S3Storage("b", "ap-northeast-2", 3600, client=fake)
    storage.put("k.jpg", b"abc")
    assert storage.get("k.jpg") == b"abc"
    assert fake.calls[-1] == ("get_object", {"Bucket": "b", "Key": "k.jpg"})


@pytest.mark.parametrize("op", ["put", "get", "url"])
@pytest.mark.parametrize("exc", [client_error(), EndpointConnectionError(endpoint_url="https://secret-host")])
def test_s3_errors_become_502_storage_unavailable(op, exc, caplog):
    assert isinstance(exc, (ClientError, BotoCoreError))
    fake = FakeS3()
    storage = S3Storage("b", "ap-northeast-2", 3600, client=fake)
    storage.put("k.jpg", b"abc")
    fake.fail = {"put": {"put_object": exc}, "get": {"get_object": exc}, "url": {"generate_presigned_url": exc}}[op]
    caplog.set_level(logging.DEBUG)
    with pytest.raises(ApiError) as caught:
        {"put": lambda: storage.put("k2.jpg", b"x"), "get": lambda: storage.get("k.jpg"), "url": lambda: storage.url("k.jpg", "p")}[op]()
    assert (caught.value.status_code, caught.value.code) == (502, "storage_unavailable")
    assert "다시 시도" in caught.value.detail
    assert type(exc).__name__ in caplog.text  # 로그에는 오류 종류만
    assert "secret-bucket-detail" not in caplog.text and "secret-host" not in caplog.text


def test_s3_client_is_built_with_sigv4_virtual_addressing_and_no_credentials(monkeypatch):
    captured = {}

    def fake_boto_client(service, **kwargs):
        captured.update(service=service, **kwargs)
        return object()

    monkeypatch.setattr(s3_module.boto3, "client", fake_boto_client)
    s3_module.make_client("ap-northeast-2")
    assert captured["service"] == "s3" and captured["region_name"] == "ap-northeast-2"
    assert captured["config"].signature_version == "s3v4"
    assert captured["config"].s3 == {"addressing_style": "virtual"}
    assert set(captured) == {"service", "region_name", "config"}  # 액세스 키를 넘기지 않아요.


# ---------------------------------------------------------------- 저장소 선택
def test_get_storage_follows_s3_bucket_setting(s3, monkeypatch):
    assert storage_kind() == "s3" and isinstance(get_storage(), S3Storage)
    assert get_storage() is get_storage()  # 같은 설정이면 같은 객체(클라이언트를 매번 만들지 않아요)
    monkeypatch.delenv("S3_BUCKET")
    get_settings.cache_clear()
    assert storage_kind() == "local" and isinstance(get_storage(), LocalStorage)


# ---------------------------------------------------------------- LocalStorage
def test_local_storage_roundtrip_and_url(tmp_path):
    storage = LocalStorage(tmp_path / "up")
    storage.put("photos/2026/11/a.jpg", b"abc")
    assert (tmp_path / "up" / "photos" / "2026" / "11" / "a.jpg").read_bytes() == b"abc"
    assert storage.get("photos/2026/11/a.jpg") == b"abc"
    assert storage.url("photos/2026/11/a.jpg", "pid") == "/api/photos/pid/file"
    assert not list((tmp_path / "up").rglob("*.tmp"))  # 임시 파일이 남지 않아요.


def test_local_storage_rejects_keys_outside_root_and_missing_files(tmp_path):
    storage = LocalStorage(tmp_path / "up")
    for key in ("../escape.jpg", "/etc/passwd", "photos/../../escape.jpg"):
        with pytest.raises(ApiError) as caught:
            storage.put(key, b"x")
        assert caught.value.code == "storage_unavailable"
    assert not (tmp_path / "escape.jpg").exists()
    with pytest.raises(ApiError) as caught:
        storage.get("photos/2026/11/none.jpg")
    assert (caught.value.status_code, caught.value.code) == (404, "not_found")


# ---------------------------------------------------------------- 사진 파일 경로
def test_photo_file_route_serves_local_photos_only(client, headers, ai):
    a = analyze(client, headers, ai).json()
    url = a["input"]["photos"][0]["url"]
    r = client.get(url)  # <img>는 헤더를 못 보내므로 기기 ID 없이 열려요.
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.content[:2] == b"\xff\xd8"


def test_photo_file_route_is_404_in_s3_mode(client, headers, ai, s3):
    a = analyze(client, headers, ai).json()
    pid = a["input"]["photos"][0]["id"]
    assert client.get(f"/api/photos/{pid}/file").status_code == 404
    assert "get_object" not in s3.names()


def test_photo_file_route_is_404_for_mock_placeholder(client, headers):
    r = client.post("/api/analyses", data={"text": "x"}, files=[("photos", JPEG)], headers=headers)  # 가짜 모드
    pid = r.json()["input"]["photos"][0]["id"]
    assert client.get(f"/api/photos/{pid}/file").status_code == 404  # 파일이 없는 자리표시 사진
    assert client.get(f"/api/photos/{uuid.uuid4()}/file").status_code == 404


def test_photo_file_route_is_404_when_file_is_gone(client, headers, ai):
    real = analyze(client, headers, ai).json()["input"]["photos"][0]
    with Session(db.get_engine()) as s:
        key = s.get(Photo, real["id"]).s3_key
    get_storage().root.joinpath(key).unlink()  # 파일이 사라진 경우
    assert client.get(real["url"]).status_code == 404


# ---------------------------------------------------------------- S3로 저장하는 흐름
def test_analysis_with_s3_stores_key_and_returns_presigned_urls(client, headers, ai, s3):
    r = analyze(client, headers, ai)
    assert r.status_code == 201, r.text
    photo = r.json()["input"]["photos"][0]

    puts = [kw for name, kw in s3.calls if name == "put_object"]
    assert len(puts) == 1 and puts[0]["Bucket"] == "shingomate-photos"
    key = puts[0]["Key"]
    assert re.fullmatch(KEY_RE, key) and key.endswith(f"{photo['id']}.jpg")
    assert puts[0]["Body"][:2] == b"\xff\xd8" and puts[0]["ContentType"] == "image/jpeg"

    assert photo["url"] == (
        f"https://shingomate-photos.s3.ap-northeast-2.amazonaws.com/{key}?X-Amz-Expires=900"
    )
    with Session(db.get_engine()) as s:
        row = s.get(Photo, photo["id"])
        assert row.s3_key == key  # 키만 저장하고 URL은 저장하지 않아요.
        assert "amazonaws" not in str(s.get(Analysis, r.json()["id"]).result)

    # 조회할 때마다 새로 만듭니다.
    presigns = s3.names().count("generate_presigned_url")
    again = client.get(f"/api/analyses/{r.json()['id']}", headers=headers).json()
    assert again["input"]["photos"][0]["url"] == photo["url"]
    assert s3.names().count("generate_presigned_url") == presigns + 1


def test_rehearsal_rereads_photo_from_storage(client, headers, ai, s3):
    from tests.test_ai_assist import _rehearsal_out

    a, reports = setup_reports(client, headers, ai)
    parking = next(r for r in reports if r["type_id"] == "illegal_parking")
    ai.reply(_rehearsal_out())
    r = client.post(f"/api/reports/{parking['id']}/rehearsals", json={}, headers=headers)
    assert r.status_code == 200, r.text
    gets = [kw for name, kw in s3.calls if name == "get_object"]
    assert len(gets) == 1 and gets[0]["Bucket"] == "shingomate-photos" and re.fullmatch(KEY_RE, gets[0]["Key"])
    assert ai.calls[-1]["messages"][0]["content"][0]["type"] == "image"


def test_upload_review_photo_goes_to_s3_and_evidence_uses_presigned_url(client, headers, ai, s3):
    from app.schemas.ai_outputs import ReviewOutput

    _, reports = setup_reports(client, headers, ai)
    trash = next(r for r in reports if r["type_id"] == "trash_dumping")
    ai.reply(ReviewOutput(status="sufficient", message="좋아요.", retake_tip=None))
    r = client.post(
        f"/api/reports/{trash['id']}/photos", data={"scene_id": "location"}, files={"photo": upload()}, headers=headers
    )
    assert r.status_code == 201, r.text
    url = r.json()["photo"]["url"]
    assert url.startswith("https://shingomate-photos.s3.ap-northeast-2.amazonaws.com/photos/")
    ev = client.get(f"/api/reports/{trash['id']}/evidence", headers=headers).json()
    assert ev["scenes"][1]["photo"]["url"] == url
    assert ev["complete"] is True


def test_s3_put_failure_is_502_and_saves_nothing(client, headers, ai, s3):
    s3.fail = {"put_object": client_error()}
    r = analyze(client, headers, ai)
    assert r.status_code == 502 and r.json()["code"] == "storage_unavailable"
    assert count_rows(Analysis) == 0 and count_rows(Photo) == 0


def test_s3_upload_failure_keeps_scene_state(client, headers, ai, s3):
    from app.schemas.ai_outputs import ReviewOutput

    _, reports = setup_reports(client, headers, ai)
    trash = next(r for r in reports if r["type_id"] == "trash_dumping")
    s3.fail = {"put_object": client_error()}
    ai.reply(ReviewOutput(status="sufficient", message="좋아요.", retake_tip=None))
    r = client.post(
        f"/api/reports/{trash['id']}/photos", data={"scene_id": "location"}, files={"photo": upload()}, headers=headers
    )
    assert r.status_code == 502 and r.json()["code"] == "storage_unavailable"
    s3.fail = {}
    ev = client.get(f"/api/reports/{trash['id']}/evidence", headers=headers).json()
    assert ev["scenes"][1]["photo"] is None and ev["complete"] is False
    assert count_rows(Photo) == 1  # 분석 사진만 있어요.


def test_s3_presign_failure_is_502(client, headers, ai, s3):
    a = analyze(client, headers, ai).json()
    s3.fail = {"generate_presigned_url": client_error()}
    r = client.get(f"/api/analyses/{a['id']}", headers=headers)
    assert r.status_code == 502 and r.json()["code"] == "storage_unavailable"


def test_mock_mode_with_s3_bucket_never_touches_s3(client, headers, s3):
    r = client.post("/api/analyses", data={"text": "x"}, files=[("photos", JPEG)], headers=headers)
    assert r.status_code == 201
    assert r.json()["input"]["photos"][0]["url"] == "/api/mock/placeholder.svg"
    assert s3.calls == []
