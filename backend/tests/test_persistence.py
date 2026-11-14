"""DB 저장 테스트: 재시작 뒤에도 남는지, 기기 격리, 날짜별 호출 수, DB 장애, 사진 대체, 시각.

SQLite와 임시 폴더의 LocalStorage만 씁니다. PostgreSQL, S3, Anthropic에는 접속하지 않습니다.
"""

import uuid
from datetime import date, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, select

from app import db
from app.config import get_settings
from app.db import check_db as real_check_db  # conftest 가 check_db 를 가짜로 바꾸기 전의 원래 함수
from app.main import create_app
from app.models import AiUsage, Analysis, Photo, Report
from app.services import quota, store
from app.timeutil import now_kst, today_kst
from tests.conftest import JPEG, count_rows, make_image, make_sqlite_engine
from tests.test_ai_assist import analyze, make_reports, setup_reports, upload

TWO = ["trash_dumping", "illegal_parking"]


def _db_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("password=secret-password"))


def _restart(url: str) -> TestClient:
    """같은 DB 파일에 새 엔진과 새 앱을 붙입니다(서버 재시작 흉내)."""
    db._engine.dispose()
    db._engine = make_sqlite_engine(url)
    return TestClient(create_app())


# ---------------------------------------------------------------- 재시작 뒤에도 남는다
def test_mock_mode_data_survives_new_engine(tmp_path, headers):
    url = f"sqlite:///{tmp_path / 'shingo.db'}"
    db._engine = make_sqlite_engine(url)
    SQLModel.metadata.create_all(db._engine)
    c1 = TestClient(create_app())

    a = c1.post("/api/analyses", data={"text": "인도에 차가 올라와 있어요"}, files=[("photos", JPEG)], headers=headers).json()
    reports = c1.post(f"/api/analyses/{a['id']}/reports", json={"type_ids": TWO}, headers=headers).json()["reports"]
    first = reports[0]["id"]
    c1.patch(f"/api/reports/{first}", json={"current_step": 3}, headers=headers)
    before = c1.get(f"/api/reports/{first}", headers=headers).json()

    c2 = _restart(url)
    assert c2.get(f"/api/analyses/{a['id']}", headers=headers).json() == a
    items = c2.get("/api/reports", headers=headers).json()["items"]
    assert [i["type_id"] for i in items] == TWO
    after = c2.get(f"/api/reports/{first}", headers=headers).json()
    assert after == before and after["current_step"] == 3
    assert c2.get("/api/health").json()["mock"] is True


def test_real_mode_data_and_photos_survive_new_engine(tmp_path, headers, ai):
    url = f"sqlite:///{tmp_path / 'shingo.db'}"
    db._engine = make_sqlite_engine(url)
    SQLModel.metadata.create_all(db._engine)
    c1 = TestClient(create_app())

    a = analyze(c1, headers, ai).json()  # 사진 1장, overview 장면 충족
    photo = a["input"]["photos"][0]
    bytes_before = c1.get(photo["url"]).content

    c2 = _restart(url)  # 분석 뒤에 재시작. 저장된 scene_matches로 AI 없이 건을 만듭니다.
    calls = len(ai.calls)
    reports = make_reports(c2, headers, a["id"], TWO)
    trash = next(r for r in reports if r["type_id"] == "trash_dumping")
    ev = c2.get(f"/api/reports/{trash['id']}/evidence", headers=headers).json()
    assert ev["scenes"][0]["review"]["status"] == "sufficient"
    assert ev["scenes"][0]["photo"]["id"] == photo["id"]
    assert len(ai.calls) == calls  # AI를 다시 부르지 않았어요.
    assert c2.get(photo["url"]).content == bytes_before  # 파일도 그대로

    # 또 한 번 재시작해도 건과 호출 수가 남아 있어요.
    c3 = _restart(url)
    assert len(c3.get("/api/reports", headers=headers).json()["items"]) == 2
    with Session(db.get_engine()) as s:
        assert s.exec(select(AiUsage.count)).one() == 1


# ---------------------------------------------------------------- 기기 격리
def test_other_device_gets_404_for_every_resource(client, headers, ai):
    a, reports = setup_reports(client, headers, ai)
    other = {"X-Device-Id": str(uuid.uuid4())}
    rid = reports[0]["id"]
    paths = [
        ("get", f"/api/analyses/{a['id']}", None),
        ("post", f"/api/analyses/{a['id']}/reports", {"type_ids": ["trash_dumping"]}),
        ("get", f"/api/reports/{rid}", None),
        ("patch", f"/api/reports/{rid}", {"current_step": 5}),
        ("get", f"/api/reports/{rid}/evidence", None),
        ("get", f"/api/reports/{rid}/guide", None),
        ("post", f"/api/reports/{rid}/drafts", {}),
        ("post", f"/api/reports/{rid}/rehearsals", {}),
    ]
    for method, path, body in paths:
        r = getattr(client, method)(path, headers=other, **({"json": body} if body is not None else {}))
        assert r.status_code == 404 and r.json()["code"] == "not_found", (method, path)
    r = client.post(f"/api/reports/{rid}/photos", files={"photo": upload()}, headers=other)
    assert r.status_code == 404
    assert client.get(f"/api/reports/{rid}", headers=headers).json()["current_step"] == 0  # 바뀌지 않았어요.
    assert count_rows(Photo) == 1  # 다른 기기의 업로드는 저장되지 않았어요.


def test_other_device_cannot_rehearse_with_my_photo(client, headers, ai):
    a, _ = setup_reports(client, headers, ai)
    other = {"X-Device-Id": str(uuid.uuid4())}
    a2 = analyze(client, other, ai).json()
    mine = a["input"]["photos"][0]["id"]
    parking = next(r for r in make_reports(client, other, a2["id"], ["illegal_parking"]))
    r = client.post(f"/api/reports/{parking['id']}/rehearsals", json={"photo_id": mine}, headers=other)
    assert r.status_code == 404


# ---------------------------------------------------------------- AI 호출 수
def test_ai_usage_is_counted_per_kst_day(client, headers, ai, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "1")
    get_settings.cache_clear()
    today = [date(2026, 11, 14)]
    monkeypatch.setattr(quota, "today_kst", lambda: today[0])

    assert analyze(client, headers, ai).status_code == 201
    r = analyze(client, headers, ai)
    assert r.status_code == 429 and r.json()["code"] == "daily_limit_exceeded"
    today[0] = date(2026, 11, 15)  # 날짜가 바뀌면 따로 셉니다.
    assert analyze(client, headers, ai).status_code == 201
    r = analyze(client, headers, ai)
    assert r.status_code == 429

    with Session(db.get_engine()) as s:
        rows = s.exec(select(AiUsage).order_by(AiUsage.day)).all()  # type: ignore[arg-type]
    assert [(u.device_id, u.day, u.count) for u in rows] == [
        (headers["X-Device-Id"], date(2026, 11, 14), 1),
        (headers["X-Device-Id"], date(2026, 11, 15), 1),
    ]  # 429로 막힌 요청은 세지 않아요.


def test_ai_usage_has_one_row_per_device_and_day(client, headers, ai, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "5")
    get_settings.cache_clear()
    for _ in range(3):
        assert analyze(client, headers, ai).status_code == 201
    other = {"X-Device-Id": str(uuid.uuid4())}
    assert analyze(client, other, ai).status_code == 201
    with Session(db.get_engine()) as s:
        rows = s.exec(select(AiUsage)).all()
    assert sorted((u.count, u.day) for u in rows) == [(1, today_kst()), (3, today_kst())]


def test_zero_limit_blocks_without_counting(client, headers, ai, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "0")
    get_settings.cache_clear()
    r = analyze(client, headers, ai)
    assert r.status_code == 429 and count_rows(AiUsage) == 0


def test_ai_usage_is_kept_after_ai_failure(client, headers, ai):
    import anthropic
    import httpx

    ai.fail(anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")))
    r = client.post("/api/analyses", data={"text": "x"}, headers=headers)
    assert r.status_code == 502
    with Session(db.get_engine()) as s:
        assert s.exec(select(AiUsage.count)).one() == 1  # 실패한 호출도 세어 둡니다.


# ---------------------------------------------------------------- DB 장애
def test_db_unavailable_is_503_then_recovers_without_restart(client, headers, monkeypatch):
    db._ready = False
    attempts = []

    def down():
        attempts.append(1)
        raise _db_error()

    monkeypatch.setattr(db, "create_tables", down)
    r = client.get("/api/reports", headers=headers)
    assert r.status_code == 503
    assert r.json()["code"] == "db_unavailable" and "다시 시도" in r.json()["detail"]
    assert "secret-password" not in r.text

    # 바로 이어지는 요청은 연결을 다시 기다리지 않고 503입니다(2초 간격).
    assert client.post("/api/analyses", data={"text": "x"}, headers=headers).status_code == 503
    assert len(attempts) == 1
    # 앱은 떠 있고 DB가 필요 없는 경로는 됩니다.
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/procedures/trash_dumping", headers=headers).status_code == 200
    assert client.get("/api/mock/placeholder.svg").status_code == 200

    # DB가 살아나면 재시작 없이 복구됩니다.
    monkeypatch.setattr(db, "create_tables", lambda: None)
    monkeypatch.setattr(db, "RECHECK_INTERVAL_SECONDS", 0)
    assert client.get("/api/reports", headers=headers).status_code == 200


def test_db_error_during_request_is_503_without_leaking_details(client, headers, monkeypatch, caplog):
    def broken(self, *args, **kwargs):
        raise _db_error()

    monkeypatch.setattr(Session, "exec", broken)
    r = client.get("/api/reports", headers=headers)
    assert r.status_code == 503 and r.json()["code"] == "db_unavailable"
    assert "secret-password" not in r.text and "secret-password" not in caplog.text


def test_init_db_retries_every_2_seconds_up_to_15_times(monkeypatch):
    db._ready = False
    calls, sleeps = [], []

    def down():
        calls.append(1)
        raise _db_error()

    monkeypatch.setattr(db, "create_tables", down)
    monkeypatch.setattr(db.time, "sleep", sleeps.append)
    assert db.init_db() is False
    assert len(calls) == 15 and sleeps == [2.0] * 14
    assert db._ready is False


def test_init_db_stops_retrying_once_db_is_up(monkeypatch):
    db._ready = False
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 4:
            raise _db_error()

    monkeypatch.setattr(db, "create_tables", flaky)
    monkeypatch.setattr(db.time, "sleep", sleeps.append)
    assert db.init_db() is True
    assert len(calls) == 4 and sleeps == [2.0] * 3
    assert db._ready is True


def test_app_starts_even_if_init_db_fails(monkeypatch, headers):
    db._ready = False
    started = []
    monkeypatch.setattr(db, "init_db", lambda: started.append(1) or False)
    monkeypatch.setattr(db, "create_tables", lambda: (_ for _ in ()).throw(_db_error()))
    with TestClient(create_app()) as c:  # lifespan 실행
        assert started == [1]
        assert c.get("/api/health").status_code == 200
        assert c.get("/api/reports", headers=headers).status_code == 503


def test_health_reflects_real_connection_and_storage(client, monkeypatch):
    monkeypatch.setattr(db, "check_db", real_check_db)
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "db": "ok", "mock": True, "storage": "local"}

    def bad():
        raise _db_error()

    monkeypatch.setattr(db, "get_engine", bad)
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["db"] == "unavailable"

    monkeypatch.setenv("S3_BUCKET", "some-bucket")
    get_settings.cache_clear()
    assert client.get("/api/health").json()["storage"] == "s3"


# ---------------------------------------------------------------- 사진 대체
def test_reupload_replaces_previous_photo_of_same_scene(client, headers, ai):
    _, reports = setup_reports(client, headers, ai)
    trash = next(r for r in reports if r["type_id"] == "trash_dumping")
    from app.schemas.ai_outputs import ReviewOutput

    url = f"/api/reports/{trash['id']}/photos"
    ids = []
    for status in ("insufficient", "sufficient"):
        ai.reply(ReviewOutput(status=status, message="확인했어요.", retake_tip="다시 찍어 주세요."))
        r = client.post(url, data={"scene_id": "location"}, files={"photo": upload(make_image())}, headers=headers)
        assert r.status_code == 201, r.text
        ids.append(r.json()["photo"]["id"])
    old, new = ids

    ev = client.get(f"/api/reports/{trash['id']}/evidence", headers=headers).json()
    location = next(s for s in ev["scenes"] if s["scene_id"] == "location")
    assert location["photo"]["id"] == new and location["review"]["status"] == "sufficient"
    assert ev["complete"] is True

    detail = client.get(f"/api/reports/{trash['id']}", headers=headers).json()
    photo_ids = [p["id"] for p in detail["photos"]]
    assert new in photo_ids and old not in photo_ids

    with Session(db.get_engine()) as s:  # 이전 사진의 행은 이력으로 남고, 검수 결과도 기록돼요.
        old_row, new_row = s.get(Photo, old), s.get(Photo, new)
        assert (old_row.review_status, new_row.review_status) == ("insufficient", "sufficient")
        assert (old_row.scene_id, new_row.scene_id) == ("location", "location")
        assert new_row.taken_order == old_row.taken_order + 1


def test_reupload_replaces_in_mock_mode_too(client, headers):
    a = client.post("/api/analyses", data={"text": "x"}, files=[("photos", JPEG)], headers=headers).json()
    trash = next(r for r in make_reports(client, headers, a["id"], ["trash_dumping"]))
    url = f"/api/reports/{trash['id']}/photos"
    ids = [
        client.post(url, data={"scene_id": "location"}, files={"photo": JPEG}, headers=headers).json()["photo"]["id"]
        for _ in range(2)
    ]
    ev = client.get(f"/api/reports/{trash['id']}/evidence", headers=headers).json()
    assert ev["scenes"][1]["photo"]["id"] == ids[1]
    assert ids[0] not in [p["id"] for p in client.get(f"/api/reports/{trash['id']}", headers=headers).json()["photos"]]


def test_photos_without_scene_stay_in_upload_order(client, headers, ai):
    _, reports = setup_reports(client, headers, ai)
    rid = reports[0]["id"]
    ids = [
        client.post(f"/api/reports/{rid}/photos", files={"photo": upload()}, headers=headers).json()["photo"]["id"]
        for _ in range(3)
    ]
    detail = client.get(f"/api/reports/{rid}", headers=headers).json()
    assert [p["id"] for p in detail["photos"] if p["scene_id"] is None] == ids


# ---------------------------------------------------------------- 저장 형태
def test_photo_rows_keep_key_only_never_url(client, headers, ai):
    a = analyze(client, headers, ai).json()
    pid = a["input"]["photos"][0]["id"]
    with Session(db.get_engine()) as s:
        row = s.get(Photo, pid)
        assert row.analysis_id == a["id"] and row.device_id == headers["X-Device-Id"]
        assert row.s3_key == f"photos/{now_kst().year:04d}/{now_kst().month:02d}/{pid}.jpg"
        analysis = s.get(Analysis, a["id"])
        assert "http" not in str(analysis.result) and "/api/photos" not in str(analysis.result)
        assert "input" not in analysis.result  # 사진 URL이 든 입력은 저장하지 않고 응답 때 만듭니다.


def test_analysis_and_report_columns_follow_spec(client, headers, ai):
    a, reports = setup_reports(client, headers, ai)
    with Session(db.get_engine()) as s:
        analysis = s.get(Analysis, a["id"])
        assert (analysis.address, analysis.district, analysis.dong) == ("서울시 마포구 ○○로 12", "마포구", "서교동")
        assert analysis.situation_text == "인도에 차가 올라와 있어요"
        rows = s.exec(select(Report).order_by(Report.sequence)).all()  # type: ignore[arg-type]
    assert [(r.type_id, r.sequence, r.total, r.status, r.current_step) for r in rows] == [
        ("trash_dumping", 1, 2, "preparing", 0),
        ("illegal_parking", 2, 2, "preparing", 0),
    ]
    assert rows[0].location_text == "서울시 마포구 ○○로 12" and rows[0].category == "complaint"
    assert rows[1].zone == "sidewalk" and rows[1].summary == a["summary"]


def test_duplicate_report_creation_race_is_409(client, headers, monkeypatch):
    a = client.post("/api/analyses", data={"text": "인도에 차가 올라와 있어요"}, headers=headers).json()
    assert make_reports(client, headers, a["id"], ["trash_dumping"])
    # 두 요청이 동시에 '아직 없음'을 본 상황: 유일 제약이 막아요.
    monkeypatch.setattr(store, "reports_exist_for_analysis", lambda *args: False)
    r = client.post(f"/api/analyses/{a['id']}/reports", json={"type_ids": ["trash_dumping"]}, headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "invalid_state"
    assert count_rows(Report) == 1


# ---------------------------------------------------------------- 시각
def test_times_are_stored_as_utc_and_returned_in_kst(client, headers):
    a = client.post("/api/analyses", data={"text": "x"}, files=[("photos", JPEG)], headers=headers).json()
    rid = make_reports(client, headers, a["id"], ["trash_dumping"])[0]["id"]
    for _ in range(2):  # 가짜 모드: 첫 업로드는 불충분, 두 번째부터 충분
        client.post(f"/api/reports/{rid}/photos", data={"scene_id": "location"}, files={"photo": JPEG}, headers=headers)
    filed = client.patch(f"/api/reports/{rid}", json={"status": "filed"}, headers=headers)
    assert filed.status_code == 200, filed.text
    filed = filed.json()
    listed = client.get("/api/reports", headers=headers).json()["items"][0]
    detail = client.get(f"/api/reports/{rid}", headers=headers).json()
    for value in (a["created_at"], filed["created_at"], filed["filed_at"], listed["created_at"], detail["filed_at"]):
        assert value.endswith("+09:00"), value

    with Session(db.get_engine()) as s:
        rec = s.get(Report, rid)
        assert rec.created_at.utcoffset() == timedelta(hours=9)
        raw = s.exec(text("SELECT created_at FROM reports WHERE id = :id").bindparams(id=rid)).one()[0]
    # SQLite에는 UTC 시각이 저장됩니다(PostgreSQL은 timestamptz).
    assert str(raw).startswith(rec.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
