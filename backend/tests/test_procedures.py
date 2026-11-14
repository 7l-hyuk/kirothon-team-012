import json
import shutil

import pytest
from pydantic import ValidationError

from app.services import procedures

TYPE_IDS = ["illegal_parking", "trash_dumping", "illegal_ad", "facility_damage"]


@pytest.mark.parametrize("type_id", TYPE_IDS)
def test_procedure_endpoint_returns_file_content(client, headers, type_id):
    r = client.get(f"/api/procedures/{type_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body == json.loads((procedures.DATA_DIR / f"{type_id}.json").read_text(encoding="utf-8"))
    assert body["type_id"] == type_id
    assert body["verified"] is False  # 안전신문고 화면과 대조하지 못한 값
    assert len(body["steps"]) == 7 and body["evidence_scenes"]
    assert all(s["verified"] is False for s in body["steps"])


def test_procedure_endpoint_errors(client, headers):
    r = client.get("/api/procedures/nope", headers=headers)
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert client.get("/api/procedures/trash_dumping").status_code == 400  # X-Device-Id 필요


def test_parking_data_has_zones_and_capture_rules():
    p = procedures.get_procedure("illegal_parking")
    assert [z.zone_id for z in p.zones] == [
        "fire_hydrant",
        "intersection_corner",
        "bus_stop",
        "crosswalk",
        "school_zone",
        "sidewalk",
        "no_parking_zone",
    ]
    nz = p.zone("no_parking_zone")
    assert nz is not None and nz.label == "주정차 금지구역" and nz.interval_seconds == 60
    assert nz.first_shot_tip == "번호판과 황색 실선 또는 주정차금지 표지가 함께 나오게" and nz.verified is False
    assert "황색 실선·주정차금지 표지 구간" in p.eligibility.basis
    assert p.capture_rules.same_position_required is True and p.capture_rules.photo_count_min == 2
    assert p.rehearsal_checks == ["zone", "plate_readable", "background_included"]
    assert procedures.subtitle(p) == "과태료 부과 대상 · 안전신문고"
    assert procedures.subtitle(procedures.get_procedure("trash_dumping")) == "구청 청소과 처리 · 안전신문고"
    assert procedures.subtitle(procedures.get_procedure("illegal_ad")) == "안전신문고"


def test_malformed_data_stops_startup(tmp_path):
    original = procedures.DATA_DIR
    try:
        procedures.DATA_DIR = tmp_path  # 파일이 없으면 실패
        procedures._load.cache_clear()
        with pytest.raises(FileNotFoundError):
            procedures.load_procedures()

        for t in TYPE_IDS:
            shutil.copy(original / f"{t}.json", tmp_path / f"{t}.json")
        broken = json.loads((tmp_path / "trash_dumping.json").read_text(encoding="utf-8"))
        broken["steps"] = broken["steps"][:3]  # 단계 수가 틀리면 실패
        (tmp_path / "trash_dumping.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        procedures._load.cache_clear()
        with pytest.raises(ValueError):
            procedures.load_procedures()

        broken = json.loads((original / "trash_dumping.json").read_text(encoding="utf-8"))
        broken["unknown_field"] = 1  # 모르는 필드도 실패
        (tmp_path / "trash_dumping.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        procedures._load.cache_clear()
        with pytest.raises(ValidationError):
            procedures.load_procedures()
    finally:
        procedures.DATA_DIR = original
        procedures._load.cache_clear()
