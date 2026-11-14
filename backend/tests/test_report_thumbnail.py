"""이슈 #17: GET /api/reports 의 thumbnail_url 대체 순서."""

from sqlmodel import Session, select

from app import db
from app.models import Analysis, Photo
from tests.conftest import JPEG


def _analyze(client, headers, photo_count=1, text="인도에 차가 올라와 있어요"):
    files = [("photos", JPEG)] * photo_count if photo_count else None
    r = client.post("/api/analyses", data={"text": text}, files=files, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _make(client, headers, analysis, type_ids):
    r = client.post(f"/api/analyses/{analysis['id']}/reports", json={"type_ids": type_ids}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["reports"]


def _list(client, headers):
    r = client.get("/api/reports?status=preparing", headers=headers)
    assert r.status_code == 200, r.text
    return {i["type_id"]: i for i in r.json()["items"]}


def _give_distinct_urls(analysis_id: str, item_photo_ids: dict[str, list[str]] | None = None) -> list[str]:
    """분석 사진마다 s3_key를 채워 사진별 URL(/api/photos/{id}/file)이 달라지게 합니다."""
    with Session(db.get_engine()) as s:
        photos = s.exec(
            select(Photo).where(Photo.analysis_id == analysis_id).order_by(Photo.taken_order)  # type: ignore[arg-type]
        ).all()
        for p in photos:
            p.s3_key = f"photos/2026/11/{p.id}.jpg"
        ids = [p.id for p in photos]
        if item_photo_ids is not None:
            s.get(Analysis, analysis_id).item_photo_ids = item_photo_ids
        s.commit()
        return ids


def _set_item_photos(analysis_id: str, value: dict[str, list[str]]) -> None:
    with Session(db.get_engine()) as s:
        s.get(Analysis, analysis_id).item_photo_ids = value
        s.commit()


def test_one_photo_two_reports_both_have_thumbnail(client, headers):
    a = _analyze(client, headers)
    _make(client, headers, a, ["trash_dumping", "illegal_parking"])
    items = _list(client, headers)
    assert items["trash_dumping"]["thumbnail_url"]
    assert items["illegal_parking"]["thumbnail_url"]


def test_thumbnail_is_photo_showing_own_problem(client, headers):
    a = _analyze(client, headers, photo_count=2)
    ids = _give_distinct_urls(a["id"])
    _set_item_photos(a["id"], {"trash_dumping": [ids[0]], "illegal_parking": [ids[1]]})
    _make(client, headers, a, ["trash_dumping", "illegal_parking"])
    items = _list(client, headers)
    assert items["illegal_parking"]["thumbnail_url"] == f"/api/photos/{ids[1]}/file"
    # 쓰레기 건에 장면으로 연결된 사진이 없으면 자기 문제가 보이는 첫 사진(ids[0])입니다.
    assert items["trash_dumping"]["thumbnail_url"] in (f"/api/photos/{ids[0]}/file", f"/api/photos/{ids[1]}/file")


def test_fallback_to_first_analysis_photo(client, headers):
    a = _analyze(client, headers, photo_count=2)
    ids = _give_distinct_urls(a["id"])
    _set_item_photos(a["id"], {})
    _make(client, headers, a, ["illegal_parking"])
    assert _list(client, headers)["illegal_parking"]["thumbnail_url"] == f"/api/photos/{ids[0]}/file"


def test_own_report_photo_wins_over_analysis_photo(client, headers):
    a = _analyze(client, headers, photo_count=2)
    ids = _give_distinct_urls(a["id"])
    _set_item_photos(a["id"], {"illegal_parking": [ids[1]]})
    (r,) = _make(client, headers, a, ["illegal_parking"])
    up = client.post(f"/api/reports/{r['id']}/photos", files={"photo": JPEG}, headers=headers)
    assert up.status_code in (200, 201), up.text
    own_id = up.json()["photo"]["id"]
    with Session(db.get_engine()) as s:
        s.get(Photo, own_id).s3_key = f"photos/2026/11/{own_id}.jpg"
        s.commit()
    assert _list(client, headers)["illegal_parking"]["thumbnail_url"] == f"/api/photos/{own_id}/file"


def test_text_only_report_has_null_thumbnail(client, headers):
    a = _analyze(client, headers, photo_count=0)
    _make(client, headers, a, [a["items"][0]["type_id"]])
    (item,) = _list(client, headers).values()
    assert item["thumbnail_url"] is None


def test_detail_photos_do_not_include_fallback(client, headers):
    a = _analyze(client, headers)
    reports = _make(client, headers, a, ["illegal_parking"])
    assert _list(client, headers)["illegal_parking"]["thumbnail_url"]
    detail = client.get(f"/api/reports/{reports[0]['id']}", headers=headers).json()
    assert detail["photos"] == []
