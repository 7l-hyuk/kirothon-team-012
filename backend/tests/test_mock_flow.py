import uuid

from tests.conftest import JPEG


def _analyze(client, headers, text="인도에 차가 올라와 있어요", with_photo=True):
    files = [("photos", JPEG)] if with_photo else None
    r = client.post("/api/analyses", data={"text": text}, files=files, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _make_reports(client, headers, analysis, type_ids):
    r = client.post(f"/api/analyses/{analysis['id']}/reports", json={"type_ids": type_ids}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["reports"]


def test_analysis_scenario_a(client, headers):
    a = _analyze(client, headers)
    assert a["reportable"] is True
    assert [i["type_id"] for i in a["items"]] == ["illegal_parking", "trash_dumping"]
    assert a["items"][0]["detail"] == {"zone": "sidewalk"}
    assert a["input"]["photos"][0]["url"] == "/api/mock/placeholder.svg"
    assert client.get(f"/api/analyses/{a['id']}", headers=headers).json() == a


def test_analysis_scenario_b(client, headers):
    for text in ("아파트 지하주차장 이중주차", "주차장에 차가 있어요"):
        a = _analyze(client, headers, text=text, with_photo=False)
        assert a["reportable"] is False and a["items"] == []
        assert "사유지" in a["not_reportable"]["message"]


def test_analysis_needs_text_or_photo(client, headers):
    r = client.post("/api/analyses", data={}, headers=headers)
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_analysis_rejects_bad_file_type(client, headers):
    r = client.post("/api/analyses", files=[("photos", ("a.txt", b"x", "text/plain"))], headers=headers)
    assert r.status_code == 415 and r.json()["code"] == "unsupported_media"


def test_reports_must_come_from_analysis_items(client, headers):
    b = _analyze(client, headers, text="아파트 주차장", with_photo=False)
    r = client.post(f"/api/analyses/{b['id']}/reports", json={"type_ids": ["trash_dumping"]}, headers=headers)
    assert r.status_code == 422
    a = _analyze(client, headers)
    r = client.post(f"/api/analyses/{a['id']}/reports", json={"type_ids": ["illegal_ad"]}, headers=headers)
    assert r.status_code == 422
    _make_reports(client, headers, a, ["trash_dumping"])
    r = client.post(f"/api/analyses/{a['id']}/reports", json={"type_ids": ["trash_dumping"]}, headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "invalid_state"


def test_full_flow(client, headers):
    a = _analyze(client, headers)
    r1, r2 = _make_reports(client, headers, a, ["trash_dumping", "illegal_parking"])
    assert (r1["sequence"], r1["type_id"]) == (1, "trash_dumping")
    assert (r2["sequence"], r2["type_id"]) == (2, "illegal_parking")

    # 증거: 분석 사진으로 overview는 충족, location은 비어 있음
    ev = client.get(f"/api/reports/{r1['id']}/evidence", headers=headers).json()
    assert (ev["required_count"], ev["done_count"], ev["complete"]) == (2, 1, False)
    assert ev["capture_in_app"] is True

    # 재촬영 흐름: 첫 업로드는 불충분, 두 번째는 충분
    up = lambda: client.post(  # noqa: E731
        f"/api/reports/{r1['id']}/photos", data={"scene_id": "location"}, files={"photo": JPEG}, headers=headers
    )
    first = up()
    assert first.status_code == 201
    assert first.json()["review"]["status"] == "insufficient"
    assert first.json()["review"]["retake_tip"]
    assert first.json()["evidence"]["complete"] is False
    second = up().json()
    assert second["review"]["status"] == "sufficient"
    assert second["evidence"] == {"required_count": 2, "done_count": 2, "complete": True}

    # 장면 없이 올리면 검수하지 않음
    nores = client.post(f"/api/reports/{r1['id']}/photos", files={"photo": JPEG}, headers=headers)
    assert nores.json()["review"] is None

    # 가이드: 첫 건은 건너뛰는 단계 없음, 둘째 건은 carry_over와 skipped
    g1 = client.get(f"/api/reports/{r1['id']}/guide", headers=headers).json()
    assert len(g1["steps"]) == 7 and g1["carry_over"] == []
    assert not any(s["skipped"] for s in g1["steps"])
    g2 = client.get(f"/api/reports/{r2['id']}/guide", headers=headers).json()
    assert len(g2["carry_over"]) == 3
    assert [s["order"] for s in g2["steps"] if s["skipped"]] == [1, 2, 5]

    # 문구: tone별 고정 문구가 건에 저장되고 가이드의 copy_text가 채워짐
    texts = set()
    for tone in ("default", "shorter", "politer"):
        d = client.post(f"/api/reports/{r1['id']}/drafts", json={"tone": tone}, headers=headers).json()
        assert d["tone"] == tone
        texts.add(d["text"])
    assert len(texts) == 3
    g1 = client.get(f"/api/reports/{r1['id']}/guide", headers=headers).json()
    copy = next(s for s in g1["steps"] if s["action"]["kind"] == "copy_text")
    assert copy["action"]["text"] == d["text"]

    # 사전 점검은 불법주정차만
    assert client.post(f"/api/reports/{r1['id']}/rehearsals", headers=headers).status_code == 409
    # 사전 점검 전에는 접수 완료 불가
    assert client.patch(f"/api/reports/{r2['id']}", json={"status": "filed"}, headers=headers).status_code == 409
    rh = client.post(f"/api/reports/{r2['id']}/rehearsals", json={}, headers=headers)
    assert rh.status_code == 200
    assert rh.json()["zone"] == "sidewalk" and rh.json()["passed"] is False
    assert rh.json()["capture_guide"]["interval_seconds"] == 60
    assert client.get(f"/api/reports/{r2['id']}/evidence", headers=headers).json()["complete"] is True


def test_rehearsal_needs_photo_in_mock_mode(client, headers):
    a = _analyze(client, headers, with_photo=False)  # 글만 있는 분석
    (parking,) = _make_reports(client, headers, a, ["illegal_parking"])
    url = f"/api/reports/{parking['id']}/rehearsals"
    r = client.post(url, json={}, headers=headers)
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    assert r.json()["detail"] == "사전 점검에는 사진이 필요해요. 사진을 먼저 올려 주세요."
    assert client.get(f"/api/reports/{parking['id']}/evidence", headers=headers).json()["complete"] is False

    up = client.post(f"/api/reports/{parking['id']}/photos", files={"photo": JPEG}, headers=headers)
    assert up.status_code == 201
    ok = client.post(url, json={"photo_id": up.json()["photo"]["id"]}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["zone"] == "sidewalk"
    assert client.get(f"/api/reports/{parking['id']}/evidence", headers=headers).json()["complete"] is True


def test_report_state_transitions(client, headers):
    a = _analyze(client, headers)
    r1, r2 = _make_reports(client, headers, a, ["trash_dumping", "illegal_parking"])
    url = f"/api/reports/{r1['id']}"

    detail = client.get(url, headers=headers).json()
    assert detail["status_label"] == "준비 중 · 증거 1/2"
    assert detail["next_report_id"] == r2["id"]

    # 증거 부족 → 접수 불가, 접수 전 결과 입력 불가
    assert client.patch(url, json={"status": "filed"}, headers=headers).status_code == 409
    assert client.patch(url, json={"result": "accepted"}, headers=headers).status_code == 409
    # 범위 밖 단계, 잘못된 값은 422
    assert client.patch(url, json={"current_step": 99}, headers=headers).status_code == 422
    assert client.patch(url, json={"status": "resolved"}, headers=headers).status_code == 422

    for _ in range(2):
        client.post(url + "/photos", data={"scene_id": "location"}, files={"photo": JPEG}, headers=headers)
    r = client.patch(url, json={"current_step": 7, "status": "filed", "receipt_number": "2026-0001"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "filed" and body["status_label"] == "접수 완료"
    assert body["filed_at"] and body["receipt_number"] == "2026-0001" and body["current_step"] == 7
    assert body["next_report_id"] == r2["id"]

    # 거꾸로, 같은 상태 반복은 409
    assert client.patch(url, json={"status": "filed"}, headers=headers).status_code == 409

    body = client.patch(url, json={"result": "accepted"}, headers=headers).json()
    assert body["status"] == "resolved" and body["status_label"] == "처리 완료 · 수용"
    assert body["resolved_at"] and all(t["done"] for t in body["timeline"])
    assert client.patch(url, json={"result": "unknown"}, headers=headers).status_code == 409


def test_list_reports_filters_and_isolation(client, headers):
    a = _analyze(client, headers)
    _make_reports(client, headers, a, ["trash_dumping", "illegal_parking"])
    other = {"X-Device-Id": str(uuid.uuid4())}

    items = client.get("/api/reports", headers=headers).json()["items"]
    assert [i["type_id"] for i in items] == ["trash_dumping", "illegal_parking"]
    assert all(i["resumable"] and i["district"] == "마포구" for i in items)
    assert client.get("/api/reports?status=filed", headers=headers).json()["items"] == []
    one = client.get("/api/reports?status=preparing&limit=1", headers=headers).json()
    assert len(one["items"]) == 1 and one["next_cursor"] == "1"
    assert client.get("/api/reports?limit=0", headers=headers).status_code == 422

    # 다른 기기는 아무것도 볼 수 없고 404
    assert client.get("/api/reports", headers=other).json()["items"] == []
    rid = items[0]["id"]
    for path in (f"/api/reports/{rid}", f"/api/reports/{rid}/evidence", f"/api/reports/{rid}/guide"):
        r = client.get(path, headers=other)
        assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert client.get(f"/api/analyses/{a['id']}", headers=other).status_code == 404
    assert client.post(f"/api/reports/{rid}/drafts", json={}, headers=other).status_code == 404
    assert client.get("/api/reports/unknown-id", headers=headers).status_code == 404
