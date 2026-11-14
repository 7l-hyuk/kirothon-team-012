"""사례 공유 테스트. Anthropic, PostgreSQL, S3에는 접속하지 않습니다(가짜 클라이언트, SQLite, 임시 폴더)."""

import re
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import db
from app.config import get_settings
from app.main import app
from app.models import AiUsage, Case, CaseDraft, CaseLike, CasePhoto, Photo, Report
from app.schemas.ai_outputs import CaseDraftOutput, ReviewOutput
from app.seed import SEED_DEVICE_ID, load_seed_cases, seed_case_photos, seed_cases
from app.services.cases import HEADINGS, scrub
from app.timeutil import now_kst
from tests.conftest import JPEG, count_rows
from tests.test_ai_assist import analysis_a, setup_reports, upload

RECEIPT = "2026-AB-7777"
ADDRESS = "서울시 마포구 ○○로 12"


# ---------------------------------------------------------------- 도우미
def other_headers() -> dict[str, str]:
    return {"X-Device-Id": str(uuid.uuid4())}


def mock_report(client, headers, *, file: bool = True) -> str:
    """가짜 모드에서 접수 완료까지 마친 쓰레기 무단투기 건의 ID."""
    a = client.post(
        "/api/analyses", data={"text": "골목에 쓰레기가 쌓여 있어요"}, files=[("photos", JPEG)], headers=headers
    ).json()
    r = client.post(f"/api/analyses/{a['id']}/reports", json={"type_ids": ["trash_dumping"]}, headers=headers)
    rid = r.json()["reports"][0]["id"]
    if file:
        for _ in range(2):  # 가짜 모드: 첫 업로드는 불충분, 두 번째부터 충분
            client.post(f"/api/reports/{rid}/photos", data={"scene_id": "location"}, files={"photo": JPEG}, headers=headers)
        p = client.patch(f"/api/reports/{rid}", json={"status": "filed", "receipt_number": "2026-0001"}, headers=headers)
        assert p.status_code == 200, p.text
    return rid


def draft_out(**over) -> CaseDraftOutput:
    data = dict(
        title="전봇대 아래 쓰레기, 사진 2장으로 접수했어요",
        situation="마포구에서 전봇대 아래 쌓인 쓰레기를 봤어요. 지나다니기 불편했어요.",
        photos="쓰레기 전체가 보이는 사진과 주변이 보이는 사진을 준비했어요. 둘 다 검수에서 충분하다고 나왔어요.",
        filing="안전신문고의 생활불편 신고 메뉴로 접수했어요. 사진을 첨부하고 내용을 붙여 넣었어요.",
        result="접수까지 마쳤고 결과를 기다리고 있어요.",
        tip="주변 건물이나 도로명이 함께 나오게 찍으면 위치를 알려 주기 좋아요.",
    )
    data.update(over)
    return CaseDraftOutput(**data)


def ai_report(client, headers, ai, **over) -> str:
    """실제 모드(가짜 Claude)에서 접수 완료까지 마친 쓰레기 무단투기 건의 ID."""
    _, reports = setup_reports(client, headers, ai, out=analysis_a(**over), type_ids=("trash_dumping",))
    rid = reports[0]["id"]
    ai.reply(ReviewOutput(status="sufficient", message="위치가 잘 보여요.", retake_tip=None))
    up = client.post(f"/api/reports/{rid}/photos", data={"scene_id": "location"}, files={"photo": upload()}, headers=headers)
    assert up.status_code == 201, up.text
    p = client.patch(f"/api/reports/{rid}", json={"status": "filed", "receipt_number": RECEIPT}, headers=headers)
    assert p.status_code == 200, p.text
    return rid


def seed() -> int:
    with Session(db.get_engine()) as session:
        return seed_cases(session)


def seed_case_photos_run(images_dir=None) -> int:
    with Session(db.get_engine()) as session:
        return seed_case_photos(session) if images_dir is None else seed_case_photos(session, images_dir)


def usage(device_id: str) -> int:
    with Session(db.get_engine()) as session:
        row = session.exec(select(AiUsage).where(AiUsage.device_id == device_id)).first()
        return row.count if row else 0


def bodies(preview: dict) -> list[str]:
    return [s["body"] for s in preview["sections"]]


def user_text(ai, index: int = -1) -> str:
    return ai.calls[index]["messages"][0]["content"][0]["text"]


# ---------------------------------------------------------------- 미리보기와 공유 (가짜 모드)
def test_preview_of_preparing_report_is_409(client, headers):
    rid = mock_report(client, headers, file=False)
    r = client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    assert r.status_code == 409 and r.json()["code"] == "invalid_state"
    r = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers)
    assert r.status_code == 409
    assert count_rows(Case) == 0


def test_share_without_consent_is_422(client, headers):
    rid = mock_report(client, headers)
    for body in ({"consent": False}, {}, {"consent": "yes"}, {"consent": None}):
        r = client.post(f"/api/reports/{rid}/case", json=body, headers=headers)
        assert r.status_code == 422 and r.json()["code"] == "validation_error", body
    assert count_rows(Case) == 0


def test_preview_shape_in_mock_mode(client, headers):
    rid = mock_report(client, headers)
    r = client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers["X-Mock"] == "true"
    body = r.json()
    now = now_kst()
    assert body["type_id"] == "trash_dumping"
    assert body["result_label"] == "결과 대기 중"
    assert body["district"] == "마포구"
    assert body["period"] == f"{now.year}년 {now.month}월"
    assert body["title"]
    assert [s["heading"] for s in body["sections"]] == list(HEADINGS)
    assert all(b.strip() for b in bodies(body))
    assert len(body["photos"]) == 2
    assert body["removed"] == [
        {"label": "상세 주소", "treatment": "구 단위까지만 표시"},
        {"label": "날짜와 시각", "treatment": "월 단위까지만 표시"},
        {"label": "접수번호", "treatment": "삭제"},
    ]
    assert body["photo_notice"] == "사진은 가리지 않고 그대로 공개돼요."
    assert "2026-0001" not in r.text  # 접수번호는 어디에도 나오지 않아요.
    assert count_rows(AiUsage) == 0  # 가짜 모드는 호출 수를 세지 않아요.


def test_preview_of_other_devices_report_is_404(client, headers):
    rid = mock_report(client, headers)
    r = client.get(f"/api/reports/{rid}/case-preview", headers=other_headers())
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=other_headers()).status_code == 404


def test_share_uses_previewed_text_and_rejects_duplicates(client, headers):
    rid = mock_report(client, headers)
    preview = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    assert client.get(f"/api/reports/{rid}", headers=headers).json()["case_id"] is None

    r = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers)
    assert r.status_code == 201, r.text
    case = r.json()
    assert case["title"] == preview["title"]
    assert [s["body"] for s in case["sections"]] == bodies(preview)
    assert [s["heading"] for s in case["sections"]] == list(HEADINGS)
    assert case["period"] == preview["period"] and case["district"] == preview["district"]
    assert case["result_label"] == preview["result_label"]
    assert case["type_label"] == "쓰레기 무단투기"
    assert (case["like_count"], case["liked_by_me"], case["is_mine"]) == (0, False, True)
    # 사진은 "어떤 사진을 준비했나" 절에 붙어요.
    assert [p["id"] for p in case["sections"][1]["photos"]] == [p["id"] for p in preview["photos"]]
    assert all(s["photos"] == [] for i, s in enumerate(case["sections"]) if i != 1)
    assert client.get(f"/api/reports/{rid}", headers=headers).json()["case_id"] == case["id"]

    dup = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers)
    assert dup.status_code == 409 and dup.json()["code"] == "invalid_state"
    assert count_rows(Case) == 1 and count_rows(CaseDraft) == 1
    assert count_rows(CasePhoto) == 2


def test_other_device_can_read_case_but_not_remove_it(client, headers):
    rid = mock_report(client, headers)
    case = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).json()
    other = other_headers()

    got = client.get(f"/api/cases/{case['id']}", headers=other)
    assert got.status_code == 200
    assert (got.json()["is_mine"], got.json()["liked_by_me"]) == (False, False)
    assert client.get(f"/api/cases/{case['id']}", headers=headers).json()["is_mine"] is True
    listed = client.get("/api/cases", headers=other).json()["items"]
    assert [i["id"] for i in listed] == [case["id"]]

    r = client.delete(f"/api/reports/{rid}/case", headers=other)
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert count_rows(Case) == 1
    assert client.get("/api/cases/nope", headers=other).status_code == 404


def test_unshare_removes_case_likes_and_links_but_keeps_report_and_photos(client, headers):
    rid = mock_report(client, headers)
    case = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).json()
    client.put(f"/api/cases/{case['id']}/like", headers=other_headers())
    photos_before = count_rows(Photo)
    assert count_rows(CaseLike) == 1

    assert client.delete(f"/api/reports/{rid}/case", headers=headers).status_code == 204
    assert client.get("/api/cases", headers=headers).json()["items"] == []
    assert client.get(f"/api/cases/{case['id']}", headers=headers).status_code == 404
    assert client.get(f"/api/reports/{rid}", headers=headers).json()["case_id"] is None
    assert (count_rows(Case), count_rows(CaseLike), count_rows(CasePhoto)) == (0, 0, 0)
    assert count_rows(Photo) == photos_before and count_rows(Report) == 1  # 신고 건과 사진은 남아요.
    # 공유하지 않은 건을 내리면 404예요.
    assert client.delete(f"/api/reports/{rid}/case", headers=headers).status_code == 404
    # 다시 공유할 수 있어요.
    assert client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).status_code == 201


def test_case_endpoints_need_device_id(client):
    for path in ("/api/cases", "/api/cases/x"):
        assert client.get(path).status_code == 400


# ---------------------------------------------------------------- 사례 목록, 필터, 예시 사례
def test_seed_inserts_three_examples_once(client, headers):
    assert seed() == 3
    assert seed() == 0
    assert count_rows(Case) == 3

    items = client.get("/api/cases", headers=headers).json()["items"]
    assert {i["title"]: i["like_count"] for i in items} == {
        "횡단보도 위 주차, 사진 2장으로 과태료 부과까지": 24,
        "처음엔 반려됐어요. 옆모습 사진이 문제였습니다": 41,
        "전단지 신고, 전화번호 사진이 핵심이었어요": 12,
    }
    assert [i["title"] for i in items] == [  # 최신순
        "횡단보도 위 주차, 사진 2장으로 과태료 부과까지",
        "전단지 신고, 전화번호 사진이 핵심이었어요",
        "처음엔 반려됐어요. 옆모습 사진이 문제였습니다",
    ]
    assert all(i["cover_url"] is None for i in items)  # 사진 붙이기 전
    assert seed_case_photos_run() == 3
    items = client.get("/api/cases", headers=headers).json()["items"]
    assert all(i["cover_url"] for i in items)
    by_title = {i["title"]: i for i in items}
    rejected = by_title["처음엔 반려됐어요. 옆모습 사진이 문제였습니다"]
    assert (rejected["type_label"], rejected["result_label"], rejected["district"]) == (
        "불법주정차",
        "불수용 → 재신고 수용",
        "성동구",
    )

    detail = client.get(f"/api/cases/{rejected['id']}", headers=headers).json()
    assert detail["period"] == "2026년 9월"
    assert [s["heading"] for s in detail["sections"]] == list(HEADINGS)
    photo_sections = {s["heading"]: s["photos"] for s in detail["sections"]}
    assert len(photo_sections["어떤 사진을 준비했나"]) == 1
    assert all(p == [] for h, p in photo_sections.items() if h != "어떤 사진을 준비했나")
    assert detail["is_mine"] is False and detail["liked_by_me"] is False


def test_seed_file_is_valid_and_examples_cannot_be_removed(client, headers):
    cases = load_seed_cases()
    assert [c.like_count for c in cases] == [24, 41, 12]
    seed()
    with Session(db.get_engine()) as session:
        rows = session.exec(select(Case)).all()
    assert all(c.is_seed and c.device_id is None and c.report_id is None for c in rows)
    # 예시 사례를 내리는 경로는 없어요. 신고 건 ID가 아니면 404예요.
    assert client.delete(f"/api/reports/{rows[0].id}/case", headers=headers).status_code == 404


def test_startup_seeds_examples_when_cases_are_empty(headers):
    with TestClient(app) as c:  # lifespan이 돌아요.
        items = c.get("/api/cases", headers=headers).json()["items"]
        assert len(items) == 3
        assert all(i["cover_url"] for i in items)  # 시작 때 사진도 붙어요.
    with TestClient(app) as c:  # 다시 시작해도 늘지 않아요.
        assert len(c.get("/api/cases", headers=headers).json()["items"]) == 3
    assert count_rows(Case) == 3
    assert count_rows(CasePhoto) == 3


def test_seed_photos_attach_to_existing_cases_once(client, headers):
    seed()  # 사진 없이 먼저 들어가 있던 예시 사례
    assert count_rows(CasePhoto) == 0
    assert seed_case_photos_run() == 3
    assert seed_case_photos_run() == 0  # 멱등
    assert count_rows(CasePhoto) == 3
    with Session(db.get_engine()) as session:
        per_case = {}
        for cp in session.exec(select(CasePhoto)).all():
            per_case[cp.case_id] = per_case.get(cp.case_id, 0) + 1
            assert cp.position == 0
            photo = session.get(Photo, cp.photo_id)
            assert photo.device_id == SEED_DEVICE_ID
            assert photo.analysis_id is None and photo.report_id is None and photo.scene_id is None
            assert re.fullmatch(r"photos/\d{4}/\d{2}/[0-9a-f-]{36}\.jpg", photo.s3_key)
        assert set(per_case.values()) == {1} and len(per_case) == 3


def test_seed_photos_skip_missing_file(client, headers, tmp_path):
    seed()
    assert seed_case_photos_run(tmp_path / "no-such-dir") == 0  # 앱 시작을 막지 않아요.
    assert count_rows(CasePhoto) == 0
    assert count_rows(Case) == 3


def test_type_filter_limit_and_cursor(client, headers):
    seed()
    ads = client.get("/api/cases?type=illegal_ad", headers=headers).json()["items"]
    assert [i["type_id"] for i in ads] == ["illegal_ad"]
    assert len(client.get("/api/cases?type=illegal_parking", headers=headers).json()["items"]) == 2
    assert client.get("/api/cases?type=trash_dumping", headers=headers).json()["items"] == []
    assert client.get("/api/cases?type=nope", headers=headers).status_code == 422

    first = client.get("/api/cases?limit=2", headers=headers).json()
    assert len(first["items"]) == 2 and first["next_cursor"] == "2"
    second = client.get("/api/cases?limit=2&cursor=2", headers=headers).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    all_ids = [i["id"] for i in first["items"] + second["items"]]
    assert len(set(all_ids)) == 3
    assert client.get("/api/cases?limit=0", headers=headers).status_code == 422
    assert client.get("/api/cases?cursor=abc", headers=headers).status_code == 422


def test_shared_case_comes_first_and_cover_is_first_photo(client, headers):
    seed()
    rid = mock_report(client, headers)
    case = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).json()
    items = client.get("/api/cases", headers=headers).json()["items"]
    assert items[0]["id"] == case["id"]
    assert items[0]["cover_url"] == case["sections"][1]["photos"][0]["url"]


# ---------------------------------------------------------------- 도움돼요
def test_like_is_idempotent_and_per_device(client, headers):
    seed()
    item = next(i for i in client.get("/api/cases", headers=headers).json()["items"] if i["like_count"] == 41)
    url = f"/api/cases/{item['id']}/like"

    for _ in range(3):
        r = client.put(url, headers=headers)
        assert r.status_code == 200 and r.json() == {"like_count": 42, "liked_by_me": True}
    assert client.get(f"/api/cases/{item['id']}", headers=headers).json()["liked_by_me"] is True
    other = other_headers()
    assert client.get(f"/api/cases/{item['id']}", headers=other).json()["liked_by_me"] is False
    assert client.put(url, headers=other).json() == {"like_count": 43, "liked_by_me": True}
    assert count_rows(CaseLike) == 2

    for _ in range(2):
        assert client.delete(url, headers=headers).json() == {"like_count": 42, "liked_by_me": False}
    # 누른 적 없는 기기의 취소는 숫자를 바꾸지 않아요.
    assert client.delete(url, headers=other_headers()).json() == {"like_count": 42, "liked_by_me": False}
    assert client.delete(url, headers=other).json() == {"like_count": 41, "liked_by_me": False}
    assert client.get("/api/cases?type=illegal_parking", headers=headers).json()["items"][1]["like_count"] == 41

    assert client.put("/api/cases/nope/like", headers=headers).status_code == 404
    assert client.delete("/api/cases/nope/like", headers=headers).status_code == 404


# ---------------------------------------------------------------- 실제 모드(가짜 Claude): AI 호출과 비식별화
def test_preview_calls_ai_once_and_reuses_the_stored_draft(client, headers, ai):
    rid = ai_report(client, headers, ai)
    calls_before, used_before = len(ai.calls), usage(headers["X-Device-Id"])
    ai.reply(draft_out())

    first = client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    assert first.status_code == 200, first.text
    assert "X-Mock" not in first.headers
    assert len(ai.calls) == calls_before + 1
    assert usage(headers["X-Device-Id"]) == used_before + 1  # 하루 상한에 포함돼요.
    body = first.json()
    assert body["title"] == "전봇대 아래 쓰레기, 사진 2장으로 접수했어요"
    assert [s["heading"] for s in body["sections"]] == list(HEADINGS)
    assert body["sections"][0]["body"].startswith("마포구에서")
    assert body["result_label"] == "결과 대기 중"

    again = client.get(f"/api/reports/{rid}/case-preview", headers=headers)  # AI 응답을 더 쌓지 않았으니 부르면 오류예요.
    assert again.status_code == 200
    assert len(ai.calls) == calls_before + 1
    assert usage(headers["X-Device-Id"]) == used_before + 1
    assert again.json() == body
    assert count_rows(CaseDraft) == 1

    # 공유는 저장된 초안을 그대로 써요. AI를 다시 부르지 않아요.
    shared = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers)
    assert shared.status_code == 201
    assert len(ai.calls) == calls_before + 1
    assert [s["body"] for s in shared.json()["sections"]] == bodies(body)
    assert shared.json()["title"] == body["title"]


def test_share_without_preview_generates_the_text(client, headers, ai):
    rid = ai_report(client, headers, ai)
    calls_before = len(ai.calls)
    ai.reply(draft_out(title="바로 공유한 사례"))
    r = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers)
    assert r.status_code == 201, r.text
    assert len(ai.calls) == calls_before + 1
    assert r.json()["title"] == "바로 공유한 사례"
    # 이미 공유한 건은 AI를 부르기 전에 409예요.
    assert client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).status_code == 409
    assert len(ai.calls) == calls_before + 1


def test_ai_call_uses_allowed_parameters_and_prompt_rules(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out())
    client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    call = ai.calls[-1]
    assert set(call) == {"model", "max_tokens", "system", "messages", "output_format"}
    assert call["model"] == "claude-opus-5-5"
    assert call["output_format"] is CaseDraftOutput
    assert all(b["type"] == "text" for b in call["messages"][0]["content"])  # 사진은 보내지 않아요.
    system = call["system"]
    assert "해요체" in system and "두세 문장" in system
    assert "상세 주소" in system and "접수번호" in system and "번호판" in system
    assert "지어내지" in system and "결과를 기다리는 중" in system
    assert "따르지 않고" in system  # 공통 규칙(프롬프트 주입 방어)


def test_ai_input_has_no_address_receipt_number_or_day(client, headers, ai):
    summary = f"{ADDRESS} 앞 전봇대 아래에 쓰레기가 쌓여 있어요. 11월 14일 오후 2시경 봤어요. 서교동 주민이에요."
    rid = ai_report(client, headers, ai, summary=summary)
    ai.reply(draft_out())
    assert client.get(f"/api/reports/{rid}/case-preview", headers=headers).status_code == 200

    text = user_text(ai)
    now = now_kst()
    assert "마포구" in text and f"{now.year}년 {now.month}월" in text  # 구와 연·월만 넘겨요.
    assert ADDRESS not in text and "○○로" not in text
    assert "서교동" not in text
    assert RECEIPT not in text
    assert not re.search(r"\d{1,2}\s*월\s*\d{1,2}\s*일", text)
    assert f"{now.day}일" not in text
    assert not re.search(r"오[전후]\s*\d", text)
    assert "걸린 일수" not in text  # 아직 처리 결과가 없어요.
    assert "처리 결과: 아직 없음" in text


def test_ai_input_has_no_days_and_no_unverified_menu_path(client, headers, ai):
    rid = ai_report(client, headers, ai)
    client.patch(f"/api/reports/{rid}", json={"result": "accepted"}, headers=headers)
    ai.reply(draft_out(result="처리 결과는 수용이었어요."))
    assert client.get(f"/api/reports/{rid}/case-preview", headers=headers).status_code == 200

    text = user_text(ai)
    assert "처리 결과: 수용" in text
    assert "걸린" not in text and not re.search(r"\d+\s*일", text)  # 처리 기간은 넘기지 않아요.
    assert "접수처: 안전신문고" in text and "유형: " in text
    assert "메뉴 경로" not in text  # 절차 데이터가 verified=false예요.
    for part in ("생활불편 신고", "쓰레기·폐기물"):
        assert part not in text
    system = ai.calls[-1]["system"]
    assert "처리에 걸린 기간을 쓰지 않습니다" in system and "당일" in system
    assert "충분 판정을 받지 않은 항목을 충분했다고 쓰지 않습니다" in system


def test_verified_menu_path_is_passed(client, headers, ai, monkeypatch):
    from app.services import procedures

    monkeypatch.setattr(procedures.get_procedure("trash_dumping"), "verified", True)
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out())
    assert client.get(f"/api/reports/{rid}/case-preview", headers=headers).status_code == 200
    assert "메뉴 경로: 생활불편 신고 > 쓰레기·폐기물" in user_text(ai)


def test_ai_input_has_actual_rehearsal_results(client, headers, ai):
    from tests.test_ai_assist import _rehearsal_out

    _, reports = setup_reports(client, headers, ai)
    parking = next(r for r in reports if r["type_id"] == "illegal_parking")
    ai.reply(_rehearsal_out(plate_readable="insufficient", plate_detail="번호판이 가려져 있어요.", background_included="sufficient"))
    assert client.post(f"/api/reports/{parking['id']}/rehearsals", json={}, headers=headers).status_code == 200
    p = client.patch(f"/api/reports/{parking['id']}", json={"status": "filed"}, headers=headers)
    assert p.status_code == 200, p.text

    ai.reply(draft_out())
    assert client.get(f"/api/reports/{parking['id']}/case-preview", headers=headers).status_code == 200
    text = user_text(ai)
    assert "- 금지구역 확인: 충분" in text
    assert "- 번호판 식별: 불충분" in text
    assert "- 주변 배경 포함: 충분" in text
    assert "사전 점검을 마쳤어요" not in text  # 사진 검수가 아닌 사전 점검 문구를 '충분'한 장면으로 넘기지 않아요.
    assert "사전 점검에서 부족했던 항목" in text  # 보완 팁


def test_rehearsal_without_stored_checks_only_says_it_was_done(client, headers, ai):
    from app.schemas.reports import SceneReview
    from app.services import store

    _, reports = setup_reports(client, headers, ai)
    parking = next(r for r in reports if r["type_id"] == "illegal_parking")
    with Session(db.get_engine()) as session:
        rec = session.get(Report, parking["id"])
        store.set_scene(
            rec, "vehicle", store.SceneState(review=SceneReview(status="sufficient", message=store.REHEARSAL_SCENE_MESSAGE))
        )
        rec.status = "filed"
        session.add(rec)
        session.commit()
        from app.services.cases import build_facts

        facts = build_facts(session, rec)
    assert facts.rehearsal == [] and facts.evidence == []
    assert facts.rehearsal_done is True
    from app.ai import prompts

    text = prompts.case_user_text(facts)
    assert "사전 점검: 거쳤음 (항목별 결과는 알 수 없음)" in text


def test_ai_output_is_scrubbed_before_saving(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(
        draft_out(
            title="12가3456 차량 신고",
            situation=f"{ADDRESS}에서 2026년 11월 14일 오후 2시에 봤어요. 서교동 골목이에요.",
            filing=f"접수번호 {RECEIPT}로 접수했어요. 문의는 010-1234-5678로 왔어요.",
        )
    )
    body = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    text = str(body)
    for banned in (ADDRESS, "○○로", "서교동", RECEIPT, "12가3456", "010-1234-5678", "14일"):
        assert banned not in text, banned
    assert "마포구" in body["sections"][0]["body"]
    assert "2026년 11월" in body["sections"][0]["body"]
    shared = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).json()
    assert RECEIPT not in str(shared) and ADDRESS not in str(shared)


def test_result_section_never_invents_a_result_while_waiting(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out(result="수용됐고 3일 걸렸어요.", title="수용됐어요"))
    body = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    assert body["result_label"] == "결과 대기 중"
    assert "수용" not in body["title"] and "기다려요" in body["title"]  # 결과를 말하는 제목도 쓰지 않아요.
    result = body["sections"][3]["body"]
    assert "수용됐" not in result and "3일" not in result
    assert "기다리고" in result  # 접수까지 한 일과 결과를 기다리는 중이라는 사실만


def test_changed_result_regenerates_the_draft(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out())
    waiting = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    calls = len(ai.calls)

    patched = client.patch(f"/api/reports/{rid}", json={"result": "accepted"}, headers=headers)
    assert patched.status_code == 200
    ai.reply(draft_out(title="수용됐어요", result="처리 결과는 수용이었어요."))
    done = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    assert len(ai.calls) == calls + 1
    assert done["result_label"] == "수용" and done["title"] == "수용됐어요"
    assert done != waiting
    assert "처리 결과: 수용" in user_text(ai)
    assert "걸린" not in user_text(ai)  # 걸린 일수는 넘기지 않아요. resolved_at은 앱에 입력한 시각이에요.
    assert count_rows(CaseDraft) == 1  # 신고 건당 한 행이에요.

    again = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    assert again == done and len(ai.calls) == calls + 1


def test_rejected_result_label_and_reason(client, headers, ai):
    rid = ai_report(client, headers, ai)
    client.patch(
        f"/api/reports/{rid}",
        json={"result": "rejected", "result_reason": f"{ADDRESS} 위치가 불명확해요. 010-1111-2222"},
        headers=headers,
    )
    ai.reply(draft_out(result="불수용이었어요."))
    body = client.get(f"/api/reports/{rid}/case-preview", headers=headers).json()
    assert body["result_label"] == "불수용"
    text = user_text(ai)
    assert "처리 결과: 불수용" in text and "불수용 사유:" in text
    assert ADDRESS not in text and "010-1111-2222" not in text


def test_preview_counts_toward_daily_limit(client, headers, ai, monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "3")  # 분석 1 + 검수 1 + 사례 글 1
    get_settings.cache_clear()
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out())
    assert client.get(f"/api/reports/{rid}/case-preview", headers=headers).status_code == 200
    client.patch(f"/api/reports/{rid}", json={"result": "accepted"}, headers=headers)  # 초안을 새로 만들어야 해요.
    r = client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    assert r.status_code == 429 and r.json()["code"] == "daily_limit_exceeded"


def test_refusal_is_422_and_nothing_is_saved(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(None, stop_reason="refusal")
    r = client.get(f"/api/reports/{rid}/case-preview", headers=headers)
    assert r.status_code == 422 and r.json()["code"] == "ai_refused"
    assert count_rows(CaseDraft) == 0 and count_rows(Case) == 0


def test_case_photos_are_public_in_real_mode(client, headers, ai):
    rid = ai_report(client, headers, ai)
    ai.reply(draft_out())
    case = client.post(f"/api/reports/{rid}/case", json={"consent": True}, headers=headers).json()
    photos = case["sections"][1]["photos"]
    assert len(photos) == 2

    other = other_headers()
    detail = client.get(f"/api/cases/{case['id']}", headers=other).json()
    assert detail["sections"][1]["photos"] == photos  # 어느 기기에나 같은 url을 내려 줘요.
    cover = client.get("/api/cases", headers=other).json()["items"][0]["cover_url"]
    assert cover == photos[0]["url"]
    file = client.get(cover)  # <img>는 헤더를 못 보내요.
    assert file.status_code == 200 and file.headers["content-type"] == "image/jpeg"


# ---------------------------------------------------------------- 비식별화 함수, 스키마
def test_scrub_unit():
    out = scrub(
        f"{ADDRESS} 앞에서 2026년 11월 14일 오후 2시 30분경, 11월 3일, 2026-11-14, 9:45에 봤어요. "
        "번호판 12가 3456, 연락처 02-123-4567, 접수번호 AB-12345, 서교동.",
        address=ADDRESS,
        dong="서교동",
        receipt="AB-12345",
        district="마포구",
    )
    assert out == "마포구 앞에서 2026년 11월, 11월, 2026-11, 에 봤어요. 번호판 번호판, 연락처, 접수번호, 마포구."
    assert scrub(None) == "" and scrub("") == ""
    assert scrub("3시간 걸렸어요", district="마포구") == "3시간 걸렸어요"  # 오전·오후가 없는 '시간'은 그대로
    assert scrub("서울시 마포구 ○○로 12", address="서울시 마포구 ○○로 12") == "근처"  # 구를 모르면 '근처'
    assert scrub("번호 1", receipt="1") == "번호 1"  # 너무 짧은 접수번호는 글을 망가뜨리지 않게 건너뜀


def test_existing_tables_got_no_new_columns():
    assert "case_id" not in Report.__table__.c
    assert set(Report.__table__.c.keys()) >= {"id", "device_id", "analysis_id", "status"}
    assert {"report_id", "device_id", "is_seed", "like_count"} <= set(Case.__table__.c.keys())
    unique_cols = [
        sorted(c.name for c in con.columns)
        for con in CaseLike.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ["case_id", "device_id"] in unique_cols
