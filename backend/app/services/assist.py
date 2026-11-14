"""실제 모드(Claude 호출)의 분석, 증거 검수, 사전 점검, 문구 대필.

AI는 판단(요약, 근거, 판정, 문구)만 하고, 라벨, 접수처, 메뉴, 안내 단계, 간격은 절차 데이터로 서버가 조립합니다.
신고 건 조회·수정·목록·증거 체크리스트처럼 AI가 없는 로직은 app.mock.service를 두 모드가 같이 씁니다.
"""

from datetime import datetime

from fastapi import UploadFile
from sqlmodel import Session

from app.ai import analyze as analyze_ai
from app.ai import draft as draft_ai
from app.ai import rehearsal as rehearsal_ai
from app.ai import review as review_ai
from app.errors import ai_unavailable, invalid_state, not_found, validation_error
from app.mock import service as base
from app.mock.fixtures import DISCLAIMER
from app.models import Report
from app.schemas.ai_outputs import AnalysisOutput, ReviewOutput, Tone
from app.schemas.analyses import (
    AnalysisInput,
    AnalysisItem,
    AnalysisResponse,
    NotReportable,
    UnsupportedItem,
)
from app.schemas.common import Location, PhotoRef, ReviewStatus, ScenePhoto
from app.schemas.reports import (
    CaptureGuide,
    DraftOut,
    PhotoUploadOut,
    RehearsalCheck,
    RehearsalOut,
    SceneReview,
)
from app.services import photos, procedures, quota, store
from app.services.procedures import Procedure
from app.services.store import SceneMatch

UNSUPPORTED_MESSAGE = "아직 안내하지 못하는 유형이에요"
NOT_REPORTABLE_TITLE = "신고가 어려운 상황이에요"


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


# ---------------------------------------------------------------- 상황 분석
def create_analysis(
    session: Session, device_id: str, text: str | None, address: str | None, files: list[UploadFile]
) -> AnalysisResponse:
    jpegs = [photos.prepare_upload(f) for f in files]  # 형식·용량 오류는 AI를 부르기 전에 끝냅니다.
    procs = procedures.load_procedures()
    quota.consume_ai_call(session, device_id)
    out = analyze_ai.run(jpegs, text, address, procs)

    analysis_id = base.new_id()
    # 호출이 성공한 뒤에만 저장소에 올리고 DB에 넣습니다.
    rows = [
        store.new_photo(device_id, data, analysis_id=analysis_id, order=n) for n, data in enumerate(jpegs, start=1)
    ]
    refs = [store.photo_ref(p) for p in rows]
    response, matches, item_photos = build_analysis_response(
        analysis_id=analysis_id,
        created_at=base.now_kst(),
        text=text,
        address=address,
        refs=refs,
        out=out,
        procs=procs,
    )
    store.save_analysis(session, device_id, response, matches, item_photos, rows)
    return response


def build_analysis_response(
    *,
    analysis_id: str,
    created_at: datetime,
    text: str | None,
    address: str | None,
    refs: list[PhotoRef],
    out: AnalysisOutput,
    procs: dict[str, Procedure],
) -> tuple[AnalysisResponse, dict[str, list[SceneMatch]], dict[str, list[str]]]:
    items: list[AnalysisItem] = []
    matches: dict[str, list[SceneMatch]] = {}
    item_photos: dict[str, list[str]] = {}
    unsupported: list[UnsupportedItem] = []
    for u in out.unsupported_items:
        if label := _clean(u.label):
            unsupported.append(UnsupportedItem(label=label, message=UNSUPPORTED_MESSAGE))

    seen: set[str] = set()
    for it in out.items:
        proc = procs.get(it.type_id)
        if proc is None:  # 4개 유형 밖이면 안내하지 않고 '안내하지 못하는 유형'으로 보냅니다.
            label = _clean(getattr(it, "label", None)) or "알 수 없는 문제"
            unsupported.append(UnsupportedItem(label=label, message=UNSUPPORTED_MESSAGE))
            continue
        if it.type_id in seen:
            continue
        seen.add(it.type_id)
        ids: list[str] = []
        for n in it.photo_numbers:  # 범위 밖 번호와 중복은 무시합니다.
            if 1 <= n <= len(refs) and refs[n - 1].id not in ids:
                ids.append(refs[n - 1].id)
        if ids:
            item_photos[proc.type_id] = ids

        zone_def = proc.zone(it.zone) if proc.type_id == "illegal_parking" else None
        items.append(
            AnalysisItem(
                type_id=proc.type_id,
                category=proc.category,
                label=f"{proc.label} ({zone_def.label})" if zone_def else proc.label,
                subtitle=procedures.subtitle(proc),
                reason=_clean(it.reason) or f"{proc.label} 신고 대상에 해당해요.",
                detail={"zone": zone_def.zone_id} if zone_def else {},
            )
        )

        # 불법주정차는 본촬영을 안전신문고 앱에서 하므로 분석 사진으로 증거를 채우지 않습니다.
        if proc.capture_rules.same_position_required:
            continue
        scene_matches: list[SceneMatch] = []
        for m in it.satisfied_scenes:
            valid = proc.scene(m.scene_id) is not None and 1 <= m.photo_number <= len(refs)
            if valid and all(sm.scene_id != m.scene_id for sm in scene_matches):
                scene_matches.append(
                    SceneMatch(
                        scene_id=m.scene_id,
                        photo_id=refs[m.photo_number - 1].id,
                        message=_clean(m.message) or "올리신 사진으로 충분해요",
                    )
                )
        if scene_matches:
            matches[proc.type_id] = scene_matches

    not_reportable: NotReportable | None = None
    if not items:
        labels = ", ".join(p.label for p in procs.values())
        nr = out.not_reportable
        if nr is not None and _clean(nr.message):
            not_reportable = NotReportable(
                title=NOT_REPORTABLE_TITLE,
                message=nr.message.strip(),
                basis=_clean(nr.basis) or f"신고메이트는 {labels}만 안내해요.",
            )
        else:
            not_reportable = NotReportable(
                title=NOT_REPORTABLE_TITLE,
                message="아직 안내하지 못하는 유형이에요. 다른 기관이나 방법은 추측해서 알려 드리지 않아요.",
                basis=f"신고메이트는 {labels}만 안내해요.",
            )

    response = AnalysisResponse(
        id=analysis_id,
        created_at=created_at,
        input=AnalysisInput(text=text, photos=refs),
        reportable=bool(items),
        summary=_clean(out.summary) or "사진과 글을 확인했어요.",
        items=items,
        unsupported_items=unsupported,
        not_reportable=not_reportable,
        location=Location(
            address=_clean(address) or _clean(out.location.address),
            district=_clean(out.location.district),
            dong=_clean(out.location.dong),
        ),
        emergency=out.emergency,
        disclaimer=DISCLAIMER,
    )
    return response, matches, item_photos


# ---------------------------------------------------------------- 증거 검수
def _to_review(out: ReviewOutput, scene_retake_tip: str) -> SceneReview:
    if out.status == "sufficient":
        return SceneReview(status="sufficient", message=_clean(out.message) or "이 사진으로 충분해요", retake_tip=None)
    default_message = "사진이 요건에 조금 못 미쳐요." if out.status == "insufficient" else "사진을 판단하기 어려워요."
    return SceneReview(
        status=out.status,
        message=_clean(out.message) or default_message,
        retake_tip=_clean(out.retake_tip) or scene_retake_tip,  # 비어 있으면 절차 데이터의 안내로 채웁니다.
    )


def upload_photo(
    session: Session, device_id: str, rec: Report, file: UploadFile, scene_id: str | None
) -> PhotoUploadOut:
    proc = procedures.get_procedure(rec.type_id)
    scene = None
    if scene_id is not None:
        scene = proc.scene(scene_id)
        if scene is None:
            raise validation_error("알 수 없는 장면이에요.")

    jpeg = photos.prepare_upload(file)
    review = None
    if scene is not None:  # scene_id가 없으면 검수하지 않고 보관만 합니다.
        quota.consume_ai_call(session, device_id)
        review = _to_review(review_ai.run(jpeg, scene.label, scene.pass_criteria), scene.retake_tip)

    row = store.new_photo(  # 저장소에 올립니다. 실패하면 502이고 DB에는 아무것도 남지 않습니다.
        device_id,
        jpeg,
        report_id=rec.id,
        scene_id=scene_id,
        review=review,
        order=store.next_photo_order(session, rec.id),
    )
    session.add(row)
    if scene is not None:
        state = store.scene_state(rec, scene.scene_id)
        state.photo_id = row.id  # 같은 장면은 이전 사진을 대체
        state.review = review
        store.set_scene(rec, scene.scene_id, state)
    session.commit()
    photo = ScenePhoto(id=row.id, url=store.photo_url(row), scene_id=scene_id)
    return PhotoUploadOut(photo=photo, review=review, evidence=base._summary(rec))


# ---------------------------------------------------------------- 불법주정차 사전 점검
_ZONE_LABELS = {
    "insufficient": "금지구역으로 보이지 않아요",
    "undetermined": "금지구역인지 판단하기 어려워요",
}
_ZONE_FALLBACK = {
    "insufficient": "6대 금지구역(소화전, 교차로 모퉁이, 버스정류소, 횡단보도, 어린이보호구역, 인도)이 아니면 신고하기 어려워요.",
    "undetermined": "차량이 어디에 있는지 알 수 있게 주변이 함께 나오도록 다시 찍어 주세요.",
}
_PLATE_LABELS = {
    "sufficient": "번호판이 식별돼요",
    "insufficient": "번호판이 잘 안 보여요",
    "undetermined": "번호판을 확인하기 어려워요",
}
_PLATE_FALLBACK = {
    "insufficient": "번호판이 잘 보이도록 차량 뒤쪽에서 가까이 찍어 주세요.",
    "undetermined": "사진이 어둡거나 흐려요. 번호판이 또렷하게 보이도록 다시 찍어 주세요.",
}
_BG_LABELS = {
    "sufficient": "주변 배경이 함께 보여요",
    "insufficient": "주변 배경이 부족해요",
    "undetermined": "주변 배경을 확인하기 어려워요",
}
_BG_FALLBACK = {
    "insufficient": "차량만 크게 찍혔어요. 주변 경계석이나 표지, 건물이 함께 보이게 찍어 주세요.",
    "undetermined": "사진이 어둡거나 흐려요. 주변이 보이게 다시 찍어 주세요.",
}


def _check(key, status: ReviewStatus, labels: dict, fallback: dict, detail: str | None, ok_label: str | None = None):
    label = ok_label if status == "sufficient" and ok_label else labels[status]
    return RehearsalCheck(
        key=key,
        status=status,
        label=label,
        detail=None if status == "sufficient" else (_clean(detail) or fallback[status]),
    )


def rehearsal(session: Session, device_id: str, rec: Report, photo_id: str | None) -> RehearsalOut:
    if rec.type_id != "illegal_parking":
        raise invalid_state("불법주정차 건에서만 사전 점검을 할 수 있어요.")
    analysis_rec = base.get_analysis_record(session, device_id, rec.analysis_id)
    analysis = analysis_rec.response
    proc = procedures.get_procedure("illegal_parking")

    photo_id = base.select_rehearsal_photo(session, rec, analysis_rec, photo_id)
    record = store.get_photo(session, photo_id)
    if record is None or record.device_id != device_id or record.s3_key is None:
        raise not_found()

    data = store.read_photo_bytes(record)  # 분석 때 올린 사진을 저장소에서 다시 읽습니다.
    quota.consume_ai_call(session, device_id)
    out = rehearsal_ai.run(data, proc)

    zone_status: ReviewStatus = out.zone_status
    if out.zone is None and zone_status == "sufficient":  # 구역을 못 골랐는데 충분할 수는 없어요.
        zone_status = "insufficient"
    zone_def = proc.zone(out.zone)
    checks = [
        _check(
            "zone",
            zone_status,
            _ZONE_LABELS,
            _ZONE_FALLBACK,
            out.zone_detail,
            ok_label=f"금지구역: {zone_def.label}" if zone_def else None,
        ),
        _check("plate_readable", out.plate_readable, _PLATE_LABELS, _PLATE_FALLBACK, out.plate_detail),
        _check("background_included", out.background_included, _BG_LABELS, _BG_FALLBACK, out.background_detail),
    ]

    interval = zone_def.interval_seconds if zone_def else (proc.capture_rules.interval_seconds or 60)
    first_shot = zone_def.first_shot_tip if zone_def else "번호판과 주변 배경이 함께 나오게"
    template = proc.capture_guide
    assert template is not None  # 시작 때 검증됨
    guide = CaptureGuide(
        title=template.title,
        steps=[
            s.replace("{first_shot}", first_shot).replace("{interval_label}", procedures.interval_label(interval))
            for s in template.steps
        ],
        warning=template.warning,
        interval_seconds=interval,
        interval_note=proc.capture_rules.interval_note or "",
    )

    # 사전 점검을 본 것만으로 증거 단계를 완료 처리합니다(명세 5장). 금지구역이 아니라고 판정되면 완료하지 않습니다.
    if zone_def:
        rec.zone = zone_def.zone_id
    if checks[0].status != "insufficient":
        scene = proc.evidence_scenes[0]
        state = store.scene_state(rec, scene.scene_id)
        state.photo_id = photo_id
        state.review = SceneReview(status="sufficient", message=store.REHEARSAL_SCENE_MESSAGE)
        store.set_scene(rec, scene.scene_id, state)
    store.set_rehearsal_checks(rec, [(c.key, c.status) for c in checks])
    session.add(rec)
    session.commit()

    return RehearsalOut(
        passed=all(c.status == "sufficient" for c in checks),
        zone=zone_def.zone_id if zone_def else "none",
        checks=checks,
        capture_guide=guide,
    )


# ---------------------------------------------------------------- 문구 대필
def _fmt_when(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    return f"{dt.year}년 {dt.month}월 {dt.day}일 {'오전' if dt.hour < 12 else '오후'} {hour12}시 {dt.minute}분"


def make_draft(session: Session, device_id: str, rec: Report, tone: Tone) -> DraftOut:
    analysis = base.get_analysis_record(session, device_id, rec.analysis_id).response
    procs = procedures.load_procedures()
    item = next((i for i in analysis.items if i.type_id == rec.type_id), None)
    zone_def = procs[rec.type_id].zone(rec.zone)

    quota.consume_ai_call(session, device_id)
    out = draft_ai.run(
        procs,
        type_id=rec.type_id,
        zone_label=zone_def.label if zone_def else None,
        summary=analysis.summary,
        reason=item.reason if item else None,
        location=rec.location.address,
        when=_fmt_when(analysis.created_at),
        tone=tone,
    )
    text = out.text.strip()
    if not text:
        raise ai_unavailable()
    rec.draft_text = text
    session.add(rec)
    session.commit()
    return DraftOut(text=text, tone=tone)
