"""사례 공유와 사례 조회 (명세 7, 8장).

- 공유할 글은 미리보기에서 만들어 `case_drafts`에 저장하고, 공유할 때 그대로 씁니다.
- 비식별화는 AI에 넘기기 전과 AI가 돌려준 뒤 양쪽에서 `scrub()`으로 합니다. 상세 주소, 접수번호, 일(day)은 AI에 넘기지 않습니다.
- 사례 조회는 기기와 무관하고, 기기 ID는 `liked_by_me`, `is_mine` 계산에만 씁니다.
- 이 모듈은 app.mock.service를 import하지 않습니다(mock.service가 case_id 조회에 이 모듈을 씁니다).
"""

import re
from uuid import uuid4

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.ai import case as case_ai
from app.config import is_mock
from app.errors import invalid_state, not_found, validation_error
from app.models import Case, CaseDraft, CaseLike, CasePhoto, Report
from app.schemas.ai_outputs import CaseDraftOutput
from app.schemas.cases import (
    CaseDetail,
    CaseFacts,
    CaseList,
    CaseListItem,
    CasePreview,
    CaseSection,
    CaseSectionDetail,
    EvidenceFact,
    LikeOut,
    RehearsalFact,
    RemovedItem,
)
from app.schemas.common import PhotoRef
from app.services import procedures, quota, store
from app.services.typeinfo import channel_info, type_def
from app.timeutil import now_kst

HEADINGS = (
    "어떤 상황이었나",
    "어떤 사진을 준비했나",
    "어디에 어떻게 접수했나",
    "결과와 걸린 시간",
    "다음 사람을 위한 팁",
)
PHOTO_SECTION = 1  # 사진은 "어떤 사진을 준비했나" 절에 붙입니다.
PHOTO_NOTICE = "사진은 가리지 않고 그대로 공개돼요."
REMOVED = (
    RemovedItem(label="상세 주소", treatment="구 단위까지만 표시"),
    RemovedItem(label="날짜와 시각", treatment="월 단위까지만 표시"),
    RemovedItem(label="접수번호", treatment="삭제"),
)
RESULT_LABELS = {"accepted": "수용", "rejected": "불수용"}
PENDING_LABEL = "결과 대기 중"
MAX_TITLE = 60


# ---------------------------------------------------------------- 비식별화
_MONTH_DAY = re.compile(r"(\d{4}\s*년\s*)?(\d{1,2})\s*월\s*\d{1,2}\s*일")
_ISO_DATE = re.compile(r"(\d{4})[-./](\d{1,2})[-./]\d{1,2}")
_AMPM_TIME = re.compile(r"(?:오전|오후)\s*\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?\s*(?:경|쯤)?")
_CLOCK = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")
_PLATE = re.compile(r"\d{2,3}\s?[가나다라마바사아자거너더러머버서어저고노도로모보소오조구누두루무부수우주하허호배]\s?\d{4}")
_PHONE = re.compile(r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}")


def scrub(
    text: str | None,
    *,
    address: str | None = None,
    dong: str | None = None,
    receipt: str | None = None,
    district: str | None = None,
) -> str:
    """사례 글에 들어가면 안 되는 값을 지웁니다. 상세 주소와 동은 구로, 일 단위 날짜는 월로 줄입니다."""
    if not text:
        return ""
    where = district or "근처"
    for secret, replacement, min_len in ((address, where, 2), (dong, where, 2), (receipt, "", 4)):
        s = (secret or "").strip()
        if len(s) >= min_len:
            text = text.replace(s, replacement)
    text = _MONTH_DAY.sub(lambda m: f"{m.group(1) or ''}{m.group(2)}월", text)
    text = _ISO_DATE.sub(lambda m: f"{m.group(1)}-{int(m.group(2)):02d}", text)
    text = _AMPM_TIME.sub("", text)
    text = _CLOCK.sub("", text)
    text = _PLATE.sub("번호판", text)
    text = _PHONE.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r"\s+([,.])", r"\1", text).strip()


def _scrub_for(rec: Report, text: str | None) -> str:
    return scrub(
        text, address=rec.location_text, dong=rec.dong, receipt=rec.receipt_number, district=rec.district
    )


# ---------------------------------------------------------------- 자료와 고정 형식 글
def _period(rec: Report) -> str:
    when = rec.filed_at or rec.created_at
    return f"{when.year}년 {when.month}월"


def _result_key(rec: Report) -> str:
    return rec.result if rec.result in RESULT_LABELS else "pending"


def result_label(rec: Report) -> str:
    return RESULT_LABELS.get(rec.result or "", PENDING_LABEL)


def _fingerprint(rec: Report) -> str:
    return f"{rec.status}|{rec.result or ''}|{rec.result_reason or ''}"


REHEARSAL_LABELS = {
    "zone": "금지구역 확인",
    "plate_readable": "번호판 식별",
    "background_included": "주변 배경 포함",
}


def build_facts(session: Session, rec: Report) -> CaseFacts:
    proc = procedures.get_procedure(rec.type_id)
    zone_def = proc.zone(rec.zone)
    channel_name, _, menu_path = channel_info(rec.type_id, rec.zone)
    if not proc.verified:  # 확인되지 않은 메뉴 경로는 AI에 넘기지 않고 접수처 이름과 유형만 넘깁니다.
        menu_path = []

    rehearsal = [
        RehearsalFact(label=REHEARSAL_LABELS.get(key, key), status=status)  # type: ignore[arg-type]
        for key, status in store.rehearsal_checks(rec)
    ]
    rehearsal_done = bool(rehearsal)

    evidence: list[EvidenceFact] = []
    tips: list[str] = []
    for scene in type_def(rec.type_id).scenes:
        review = store.scene_state(rec, scene.scene_id).review
        if review is None:
            continue
        if review.message == store.REHEARSAL_SCENE_MESSAGE:
            # 사진 검수가 아니라 사전 점검이 채운 장면이에요. 항목별 판정이 따로 있어서 '충분'으로 넘기지 않습니다.
            rehearsal_done = True
            continue
        evidence.append(
            EvidenceFact(
                label=scene.label,
                required=scene.required,
                status=review.status,
                message=_scrub_for(rec, review.message) or None,
            )
        )
        data_scene = proc.scene(scene.scene_id)
        if review.status != "sufficient" and data_scene is not None:
            tips.append(f"'{scene.label}' 사진은 이렇게 찍으면 돼요. {data_scene.retake_tip}")
    if any(r.status != "sufficient" for r in rehearsal) and proc.evidence_scenes:
        tips.append(f"사전 점검에서 부족했던 항목은 이렇게 보완하면 돼요. {proc.evidence_scenes[0].retake_tip}")
    if not tips:
        first = next((s for s in proc.evidence_scenes if s.required), None)
        if first is not None and not proc.capture_rules.same_position_required:
            tips.append(f"'{first.label}'은 '{first.pass_criteria}'가 기준이에요.")

    capture_note = capture_warning = None
    if proc.capture_rules.same_position_required:
        interval = zone_def.interval_seconds if zone_def else proc.capture_rules.interval_seconds
        gap = f" {procedures.interval_label(interval)} 간격으로" if interval else ""
        capture_note = (
            f"본촬영은 안전신문고 앱에서 같은 위치, 같은 방향으로{gap} "
            f"{proc.capture_rules.photo_count_min}장을 찍어야 해요. 이 앱에서는 사전 점검으로 확인해요."
        )
        capture_warning = proc.capture_guide.warning if proc.capture_guide else None

    key = _result_key(rec)
    return CaseFacts(
        type_id=rec.type_id,  # type: ignore[arg-type]
        label=rec.label,
        kind="신고" if rec.category == "report" else "민원",
        zone_label=zone_def.label if zone_def else None,
        summary=_scrub_for(rec, rec.summary) or "상황 요약이 없어요.",
        district=rec.district,
        period=_period(rec),
        photo_count=len(store.report_photos(session, rec)),
        evidence=evidence,
        rehearsal_done=rehearsal_done,
        rehearsal=rehearsal,
        agency=proc.agency,
        channel_name=channel_name,
        menu_path=menu_path,
        capture_note=capture_note,
        capture_warning=capture_warning,
        tips=tips,
        filed=rec.status != "preparing",
        result=key,  # type: ignore[arg-type]
        result_label=result_label(rec),
        result_reason=_scrub_for(rec, rec.result_reason) or None,
    )


def fallback_output(facts: CaseFacts) -> CaseDraftOutput:
    """신고 건 자료로 조립한 고정 형식의 글. 가짜 모드와, AI가 빈 값을 줬을 때 씁니다."""
    where = f"{facts.district}에서" if facts.district else "길에서"
    situation = f"{where} '{facts.label}' 상황을 만났어요. {facts.summary}"

    parts: list[str] = []
    if facts.evidence:
        names = ", ".join(f"'{e.label}'" for e in facts.evidence)
        ok = sum(1 for e in facts.evidence if e.status == "sufficient")
        parts.append(f"검수를 거친 장면은 {names}예요. 그중 {ok}개가 충분하다는 결과를 받았어요.")
    if facts.rehearsal:
        names = {"sufficient": "충분", "insufficient": "불충분", "undetermined": "판단 불가"}
        checks = ", ".join(f"{r.label} {names[r.status]}" for r in facts.rehearsal)
        parts.append(f"사전 점검 결과는 {checks}이었어요.")
    elif facts.rehearsal_done:
        parts.append("사전 점검을 거쳤어요.")
    if facts.photo_count:
        parts.append(f"올린 사진은 모두 {facts.photo_count}장이에요.")
    if facts.capture_note:
        parts.append(facts.capture_note)
    photos = " ".join(parts) or "이 건에서는 따로 올린 사진이 없어요."

    if facts.menu_path:
        filing = f"{facts.channel_name}의 '{' > '.join(facts.menu_path)}' 메뉴로 접수했어요."
    else:
        filing = f"{facts.channel_name}에서 '{facts.label}' 건으로 접수했어요."
    if facts.agency:
        filing += f" 처리는 {facts.agency}에서 맡아요."

    result = _fallback_result(facts)

    tips = list(facts.tips[:2])
    if facts.capture_warning:
        tips.append(facts.capture_warning)
    tip = " ".join(tips) or "접수하기 전에 필요한 사진 장면을 미리 확인해 두면 좋아요."

    titles = {
        "accepted": f"{facts.label}, 수용됐어요",
        "rejected": f"{facts.label}, 불수용됐어요",
        "pending": f"{facts.label}, 접수하고 결과를 기다려요",
    }
    return CaseDraftOutput(
        title=titles[facts.result], situation=situation, photos=photos, filing=filing, result=result, tip=tip
    )


def _fallback_result(facts: CaseFacts) -> str:
    """'결과와 걸린 시간' 절. 결과만 씁니다. 처리 기간은 앱에 입력한 시각으로는 알 수 없어서 쓰지 않습니다."""
    if facts.result == "pending":
        return "접수까지 마쳤고, 지금은 처리 결과를 기다리고 있어요."
    text = "처리 결과는 수용이에요." if facts.result == "accepted" else "처리 결과는 불수용이었어요."
    if facts.result == "rejected":
        text += f" 사유는 '{facts.result_reason}'이라고 적었어요." if facts.result_reason else " 사유는 따로 적지 않았어요."
    return text


def _tidy(rec: Report, out: CaseDraftOutput, facts: CaseFacts) -> CaseDraftOutput:
    """AI 출력을 비식별화하고, 빈 값은 고정 형식 글로 채웁니다. 결과가 없으면 결과 절은 항상 고정 형식입니다."""
    fb = fallback_output(facts)

    def pick(value: str, default: str) -> str:
        return _scrub_for(rec, value) or default

    result = fb.result if facts.result == "pending" else pick(out.result, fb.result)
    title = pick(out.title, fb.title)
    if facts.result == "pending" and re.search(r"수용|반려", title):  # 결과가 없는데 결과를 말하는 제목은 쓰지 않습니다.
        title = fb.title
    return CaseDraftOutput(
        title=title[:MAX_TITLE],
        situation=pick(out.situation, fb.situation),
        photos=pick(out.photos, fb.photos),
        filing=pick(out.filing, fb.filing),
        result=result,
        tip=pick(out.tip, fb.tip),
    )


# ---------------------------------------------------------------- 초안
def _sections(out: CaseDraftOutput) -> list[dict[str, str]]:
    bodies = (out.situation, out.photos, out.filing, out.result, out.tip)
    return [{"heading": h, "body": b} for h, b in zip(HEADINGS, bodies, strict=True)]


def _get_report(session: Session, device_id: str, report_id: str) -> Report:
    rec = store.get_report(session, device_id, report_id)
    if rec is None:
        raise not_found()
    return rec


def _require_filed(rec: Report) -> None:
    if rec.status == "preparing":
        raise invalid_state("접수를 마친 뒤에 사례로 공유할 수 있어요.")


def _draft_for(session: Session, report_id: str) -> CaseDraft | None:
    return session.exec(select(CaseDraft).where(CaseDraft.report_id == report_id)).first()


def ensure_draft(session: Session, device_id: str, rec: Report) -> CaseDraft:
    """저장된 초안을 돌려줍니다. 없거나 처리 결과가 바뀌었으면 새로 만들어 저장합니다(이때만 AI를 부릅니다)."""
    fingerprint = _fingerprint(rec)
    draft = _draft_for(session, rec.id)
    if draft is not None and draft.fingerprint == fingerprint:
        return draft

    facts = build_facts(session, rec)
    if is_mock():
        out = fallback_output(facts)
    else:
        quota.consume_ai_call(session, device_id)
        out = _tidy(rec, case_ai.run(facts, procedures.get_procedure(rec.type_id)), facts)

    if draft is None:
        draft = CaseDraft(report_id=rec.id, device_id=device_id, fingerprint=fingerprint, title="", result_label="", period="")
    draft.fingerprint = fingerprint
    draft.title = out.title
    draft.sections = _sections(out)
    draft.result_label = facts.result_label
    draft.district = rec.district
    draft.period = facts.period
    draft.created_at = now_kst()
    session.add(draft)
    try:
        session.commit()
    except IntegrityError:  # 같은 건의 동시 요청이 먼저 저장했어요. 그 초안을 씁니다.
        session.rollback()
        existing = _draft_for(session, rec.id)
        if existing is None:
            raise
        return existing
    return draft


# ---------------------------------------------------------------- 7장: 미리보기, 공유, 내리기
def preview(session: Session, device_id: str, report_id: str) -> CasePreview:
    rec = _get_report(session, device_id, report_id)
    _require_filed(rec)
    draft = ensure_draft(session, device_id, rec)
    photos = [PhotoRef(id=p.id, url=p.url) for p in store.report_photos(session, rec)]
    return CasePreview(
        title=draft.title,
        type_id=rec.type_id,  # type: ignore[arg-type]
        result_label=draft.result_label,
        district=draft.district,
        period=draft.period,
        sections=[CaseSection(**s) for s in draft.sections],
        photos=photos,
        removed=list(REMOVED),
        photo_notice=PHOTO_NOTICE,
    )


def case_id_for_report(session: Session, report_id: str) -> str | None:
    return session.exec(select(Case.id).where(Case.report_id == report_id)).first()


def share(session: Session, device_id: str, report_id: str, consent: bool) -> CaseDetail:
    rec = _get_report(session, device_id, report_id)
    if consent is not True:
        raise validation_error("공유하려면 동의가 필요해요.")
    _require_filed(rec)
    if case_id_for_report(session, rec.id) is not None:
        raise invalid_state("이미 공유한 신고예요.")

    draft = ensure_draft(session, device_id, rec)  # 미리보기에서 본 글을 그대로 씁니다.
    case = Case(
        id=str(uuid4()),
        report_id=rec.id,
        device_id=device_id,
        type_id=rec.type_id,
        title=draft.title,
        sections=draft.sections,
        result_label=draft.result_label,
        district=draft.district,
        period=draft.period,
        like_count=0,
        is_seed=False,
        created_at=now_kst(),
    )
    session.add(case)
    try:
        session.flush()  # 부모(사례)를 먼저 넣고 사진 연결을 넣습니다.
        session.add_all(
            CasePhoto(case_id=case.id, photo_id=p.id, position=n)
            for n, p in enumerate(store.report_photos(session, rec))
        )
        session.commit()
    except IntegrityError:  # 같은 건을 동시에 두 번 공유했어요 (cases.report_id 유일 제약)
        session.rollback()
        raise invalid_state("이미 공유한 신고예요.") from None
    return _detail(session, case, device_id)


def unshare(session: Session, device_id: str, report_id: str) -> None:
    rec = _get_report(session, device_id, report_id)
    case = session.exec(select(Case).where(Case.report_id == rec.id)).first()
    if case is None:
        raise not_found()
    # 자식 행을 먼저 지웁니다. 신고 건, 사진, 초안은 남깁니다.
    session.execute(delete(CaseLike).where(CaseLike.case_id == case.id))  # type: ignore[arg-type]
    session.execute(delete(CasePhoto).where(CasePhoto.case_id == case.id))  # type: ignore[arg-type]
    session.execute(delete(Case).where(Case.id == case.id))  # type: ignore[arg-type]
    session.commit()


# ---------------------------------------------------------------- 8장: 사례
def _type_label(type_id: str) -> str:
    return procedures.get_procedure(type_id).label


def _get_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise not_found()
    return case


def _liked(session: Session, case_id: str, device_id: str) -> bool:
    return (
        session.exec(
            select(CaseLike.id).where(CaseLike.case_id == case_id, CaseLike.device_id == device_id)  # type: ignore[arg-type]
        ).first()
        is not None
    )


def _detail(session: Session, case: Case, device_id: str) -> CaseDetail:
    photo_ids = session.exec(
        select(CasePhoto.photo_id).where(CasePhoto.case_id == case.id).order_by(CasePhoto.position)  # type: ignore[arg-type]
    ).all()
    refs = store.photo_refs(session, list(photo_ids))
    photos = [refs[i] for i in photo_ids if i in refs]
    sections = [
        CaseSectionDetail(heading=s["heading"], body=s["body"], photos=photos if n == PHOTO_SECTION else [])
        for n, s in enumerate(case.sections)
    ]
    return CaseDetail(
        id=case.id,
        title=case.title,
        type_id=case.type_id,  # type: ignore[arg-type]
        type_label=_type_label(case.type_id),
        result_label=case.result_label,
        district=case.district,
        period=case.period,
        sections=sections,
        like_count=case.like_count,
        liked_by_me=_liked(session, case.id, device_id),
        is_mine=not case.is_seed and case.device_id == device_id,
        created_at=case.created_at,
    )


def get_case(session: Session, device_id: str, case_id: str) -> CaseDetail:
    return _detail(session, _get_case(session, case_id), device_id)


def list_cases(session: Session, type_id: str | None, limit: int, cursor: str | None) -> CaseList:
    try:
        offset = int(cursor) if cursor else 0
        if offset < 0:
            raise ValueError
    except ValueError:
        raise validation_error("'cursor' 값을 확인해 주세요.") from None

    stmt = select(Case)
    if type_id:
        stmt = stmt.where(Case.type_id == type_id)
    stmt = stmt.order_by(Case.created_at.desc(), Case.id)  # type: ignore[attr-defined]
    rows = session.exec(stmt.offset(offset).limit(limit + 1)).all()
    page, has_more = rows[:limit], len(rows) > limit

    first_photo: dict[str, str] = {}
    if page:
        links = session.exec(
            select(CasePhoto)
            .where(CasePhoto.case_id.in_([c.id for c in page]))  # type: ignore[attr-defined]
            .order_by(CasePhoto.case_id, CasePhoto.position)  # type: ignore[arg-type]
        ).all()
        for link in links:
            first_photo.setdefault(link.case_id, link.photo_id)
    refs = store.photo_refs(session, list(first_photo.values()))

    items = [
        CaseListItem(
            id=c.id,
            title=c.title,
            type_id=c.type_id,  # type: ignore[arg-type]
            type_label=_type_label(c.type_id),
            result_label=c.result_label,
            district=c.district,
            like_count=c.like_count,
            cover_url=refs[first_photo[c.id]].url if c.id in first_photo and first_photo[c.id] in refs else None,
        )
        for c in page
    ]
    return CaseList(items=items, next_cursor=str(offset + limit) if has_more else None)


# ---------------------------------------------------------------- 도움돼요
def _like_out(session: Session, case_id: str, device_id: str) -> LikeOut:
    count = session.exec(select(Case.like_count).where(Case.id == case_id)).one()  # type: ignore[arg-type]
    return LikeOut(like_count=count, liked_by_me=_liked(session, case_id, device_id))


def like(session: Session, device_id: str, case_id: str) -> LikeOut:
    _get_case(session, case_id)
    if not _liked(session, case_id, device_id):
        try:
            session.add(CaseLike(case_id=case_id, device_id=device_id))
            session.flush()  # 유일 제약 위반이면 여기서 납니다(이미 눌린 것으로 봅니다).
            session.execute(update(Case).where(Case.id == case_id).values(like_count=Case.like_count + 1))  # type: ignore[arg-type]
            session.commit()
        except IntegrityError:
            session.rollback()
    return _like_out(session, case_id, device_id)


def unlike(session: Session, device_id: str, case_id: str) -> LikeOut:
    _get_case(session, case_id)
    result = session.execute(
        delete(CaseLike).where(CaseLike.case_id == case_id, CaseLike.device_id == device_id)  # type: ignore[arg-type]
    )
    if result.rowcount == 1:
        session.execute(
            update(Case).where(Case.id == case_id, Case.like_count > 0).values(like_count=Case.like_count - 1)  # type: ignore[arg-type]
        )
    session.commit()
    return _like_out(session, case_id, device_id)
