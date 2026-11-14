"""신고 건의 상태 전이와 응답 조립. 가짜 모드의 응답 값과, 두 모드가 같이 쓰는 신고 건 로직을 둡니다.

상태는 DB(app.services.store)에 저장하고, 세션은 라우터가 요청마다 열어 넘겨 줍니다.
이 모듈은 AI와 S3를 직접 부르지 않습니다. 쓰는 함수는 마지막에 커밋합니다.
"""

from datetime import datetime
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import is_mock
from app.errors import invalid_state, not_found, validation_error
from app.mock import fixtures
from app.mock.catalog import WEB_URL, SceneDef, TypeDef
from app.models import Report
from app.schemas.analyses import (
    AnalysisResponse,
    CreatedReport,
    CreateReportsResponse,
)
from app.schemas.common import PhotoRef, ScenePhoto
from app.schemas.reports import (
    STEP_COUNT,
    CarryOver,
    DraftOut,
    EvidenceOut,
    EvidenceProgress,
    EvidenceScene,
    EvidenceSummary,
    GuideAction,
    GuideChannel,
    GuideOut,
    GuideStep,
    PhotoUploadOut,
    RehearsalOut,
    ReportChannel,
    ReportList,
    ReportListItem,
    ReportOut,
    ReportPatch,
    SceneReview,
    TimelineEntry,
)
from app.services import cases as case_service
from app.services import guide as procedure_guide
from app.services import photos as photo_service
from app.services import procedures, store
from app.services.store import AnalysisRecord, SceneState
from app.services.typeinfo import channel_info, type_def
from app.timeutil import KST, now_kst  # noqa: F401  (KST는 옛 import 경로 유지용)

ALLOWED_MIME = photo_service.ALLOWED_MIME
MAX_PHOTO_BYTES = photo_service.MAX_PHOTO_BYTES
MAX_PHOTOS_PER_ANALYSIS = 4
RESULT_LABEL = {"accepted": "수용", "rejected": "불수용", "unknown": "아직 몰라요"}


def new_id() -> str:
    return str(uuid4())


# ---------- 업로드 검사 (가짜 모드는 파일을 저장하지 않고 버립니다) ----------
def check_upload(file: UploadFile) -> None:
    photo_service.read_upload(file)


# ---------- 소유권 확인: 모든 조회에 기기 ID 조건을 겁니다 ----------
def get_analysis_record(session: Session, device_id: str, analysis_id: str) -> AnalysisRecord:
    rec = store.load_analysis(session, device_id, analysis_id)
    if rec is None:
        raise not_found()
    return rec


def get_report_record(session: Session, device_id: str, report_id: str) -> Report:
    rec = store.get_report(session, device_id, report_id)
    if rec is None:
        raise not_found()
    return rec


# ---------- 분석 ----------
def create_analysis(session: Session, device_id: str, text: str | None, photo_count: int) -> AnalysisResponse:
    analysis_id = new_id()
    # 가짜 모드는 파일을 저장하지 않으므로 자리표시 사진 행만 남깁니다(s3_key 없음).
    rows = [store.new_photo(device_id, None, analysis_id=analysis_id, order=n) for n in range(1, photo_count + 1)]
    response = fixtures.build_analysis(analysis_id, now_kst(), text, [store.photo_ref(p) for p in rows])
    store.save_analysis(session, device_id, response, {}, {}, rows)
    return response


def create_reports(
    session: Session, device_id: str, analysis_id: str, type_ids: list[str]
) -> CreateReportsResponse:
    analysis_rec = get_analysis_record(session, device_id, analysis_id)
    analysis = analysis_rec.response
    available = {item.type_id: item for item in analysis.items}
    if len(set(type_ids)) != len(type_ids):
        raise validation_error("같은 항목이 두 번 들어 있어요.")
    if any(t not in available for t in type_ids):
        raise validation_error("분석 결과에 없는 항목이에요.")
    if store.reports_exist_for_analysis(session, device_id, analysis_id):
        raise invalid_state("이미 신고 건을 만들었어요. 내 신고에서 이어서 해 주세요.")

    created_at = now_kst()
    first_photo = analysis.input.photos[0] if analysis.input.photos else None
    rows: list[Report] = []
    for seq, type_id in enumerate(type_ids, start=1):
        item = available[type_id]
        # 분석 사진으로 이미 충족한 장면은 AI를 다시 부르지 않고 그대로 반영합니다.
        matched = {m.scene_id: m for m in analysis_rec.scene_matches.get(type_id, [])}
        zone = item.detail.get("zone")
        rec = Report(
            id=new_id(),
            device_id=device_id,
            analysis_id=analysis_id,
            type_id=type_id,
            category=item.category,
            label=item.label,
            sequence=seq,
            total=len(type_ids),
            situation_text=analysis.input.text,
            location_text=analysis.location.address,
            district=analysis.location.district,
            dong=analysis.location.dong,
            summary=analysis.summary,
            zone=zone if isinstance(zone, str) else None,
            scenes={},
            created_at=created_at,
        )
        for scene in type_def(type_id).scenes:
            state = SceneState()
            if is_mock():
                if scene.prefill_from_analysis and first_photo:  # 가짜 모드: 분석 사진 재사용
                    state.photo_id = first_photo.id
                    state.review = SceneReview(status="sufficient", message=scene.sufficient_message)
            elif scene.scene_id in matched:
                m = matched[scene.scene_id]
                state.photo_id = m.photo_id
                state.review = SceneReview(status="sufficient", message=m.message)
            store.set_scene(rec, scene.scene_id, state)
        rows.append(rec)

    session.add_all(rows)
    try:
        session.commit()
    except IntegrityError:  # 같은 분석에 동시에 두 번 만들었을 때 (analysis_id, sequence) 유일 제약에 걸립니다.
        session.rollback()
        raise invalid_state("이미 신고 건을 만들었어요. 내 신고에서 이어서 해 주세요.") from None
    created = [CreatedReport(id=r.id, type_id=r.type_id, sequence=r.sequence, status="preparing") for r in rows]
    return CreateReportsResponse(analysis_id=analysis_id, total=len(created), reports=created)


# ---------- 증거 ----------
def _scene_defs(rec: Report) -> tuple[SceneDef, ...]:
    return type_def(rec.type_id).scenes


def _summary(rec: Report) -> EvidenceSummary:
    defs = [d for d in _scene_defs(rec) if d.required]
    required = len(defs)
    done = sum(
        1 for d in defs if (r := store.scene_state(rec, d.scene_id).review) is not None and r.status == "sufficient"
    )
    return EvidenceSummary(required_count=required, done_count=done, complete=done >= required)


def _report_photos(session: Session, rec: Report) -> list[ScenePhoto]:
    return store.report_photos(session, rec)


def evidence_out(session: Session, rec: Report) -> EvidenceOut:
    summary = _summary(rec)
    remaining = summary.required_count - summary.done_count
    intro = (
        f"{rec.label}부터 준비할게요. 사진이 {remaining}장 더 필요해요."
        if remaining
        else f"{rec.label} 사진이 모두 준비됐어요."
    )
    if not type_def(rec.type_id).capture_in_app:
        intro = f"{rec.label}은 사전 점검으로 확인해요. 본촬영은 안전신문고 앱에서 해요."
    refs = store.scene_refs(session, rec)
    scenes = [
        EvidenceScene(
            scene_id=d.scene_id,
            label=d.label,
            required=d.required,
            photo=refs.get(d.scene_id),
            review=store.scene_state(rec, d.scene_id).review,
        )
        for d in _scene_defs(rec)
    ]
    return EvidenceOut(
        report_id=rec.id,
        label=rec.label,
        intro=intro,
        capture_in_app=type_def(rec.type_id).capture_in_app,
        scenes=scenes,
        **summary.model_dump(),
    )


def upload_photo(session: Session, device_id: str, rec: Report, scene_id: str | None) -> PhotoUploadOut:
    review: SceneReview | None = None
    state: SceneState | None = None
    if scene_id is not None:
        scene = next((d for d in _scene_defs(rec) if d.scene_id == scene_id), None)
        if scene is None:
            raise validation_error("알 수 없는 장면이에요.")
        state = store.scene_state(rec, scene_id)
        state.attempts += 1
        if state.attempts >= 2:  # 재촬영 시연: 첫 업로드는 불충분, 두 번째부터 충분
            review = SceneReview(status="sufficient", message=scene.sufficient_message)
        else:
            review = SceneReview(
                status="insufficient", message=scene.insufficient_message, retake_tip=scene.retake_tip
            )

    # 가짜 모드는 파일을 저장하지 않으므로 자리표시 사진 행만 남깁니다.
    row = store.new_photo(
        device_id,
        None,
        report_id=rec.id,
        scene_id=scene_id,
        review=review,
        order=store.next_photo_order(session, rec.id),
    )
    session.add(row)
    if state is not None and scene_id is not None:  # 같은 장면은 이전 사진을 대체
        state.photo_id = row.id
        state.review = review
        store.set_scene(rec, scene_id, state)
    session.commit()
    photo = ScenePhoto(id=row.id, url=store.photo_url(row), scene_id=scene_id)
    return PhotoUploadOut(photo=photo, review=review, evidence=_summary(rec))


def select_rehearsal_photo(
    session: Session, rec: Report, analysis_rec: AnalysisRecord, photo_id: str | None
) -> str:
    """사전 점검에 쓸 사진 ID를 고릅니다. 두 모드가 같이 씁니다.

    요청의 photo_id → 분석에서 불법주정차가 보인 사진 → 분석의 첫 사진 순서입니다.
    쓸 사진이 없으면 422, 요청한 사진이 이 건의 사진이 아니면 404입니다.
    """
    candidates = [p.id for p in analysis_rec.response.input.photos] + [p.id for p in _report_photos(session, rec)]
    if photo_id is None:
        if not candidates:
            raise validation_error("사전 점검에는 사진이 필요해요. 사진을 먼저 올려 주세요.")
        parking_photos = analysis_rec.item_photo_ids.get("illegal_parking")
        return parking_photos[0] if parking_photos else candidates[0]
    if photo_id not in candidates:
        raise not_found()
    return photo_id


def rehearsal(session: Session, device_id: str, rec: Report, photo_id: str | None) -> RehearsalOut:
    if rec.type_id != "illegal_parking":
        raise invalid_state("불법주정차 건에서만 사전 점검을 할 수 있어요.")
    analysis_rec = get_analysis_record(session, device_id, rec.analysis_id)
    analysis = analysis_rec.response
    photo_id = select_rehearsal_photo(session, rec, analysis_rec, photo_id)

    scene = _scene_defs(rec)[0]  # 사전 점검을 본 것만으로 증거 단계 완료 (명세 5장)
    state = store.scene_state(rec, scene.scene_id)
    state.photo_id = photo_id
    state.review = SceneReview(status="sufficient", message=scene.sufficient_message)
    store.set_scene(rec, scene.scene_id, state)
    session.commit()

    item = next(i for i in analysis.items if i.type_id == "illegal_parking")
    return fixtures.build_rehearsal(str(item.detail.get("zone", "sidewalk")))


# ---------- 신고 건 ----------
def _status_label(rec: Report) -> str:
    if rec.status == "preparing":
        s = _summary(rec)
        return "준비 중"
    if rec.status == "filed":
        return "접수 완료"
    return f"처리 완료 · {RESULT_LABEL.get(rec.result or '', '')}"


def _fmt_kst(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    return f"{dt.month}월 {dt.day}일 {'오전' if dt.hour < 12 else '오후'} {hour12}:{dt.minute:02d}"


def _next_report_id(session: Session, rec: Report) -> str | None:
    return session.exec(
        select(Report.id)
        .where(
            Report.device_id == rec.device_id,
            Report.analysis_id == rec.analysis_id,
            Report.sequence > rec.sequence,
            Report.status == "preparing",
        )
        .order_by(Report.sequence)  # type: ignore[arg-type]
        .limit(1)
    ).first()


def report_out(session: Session, rec: Report) -> ReportOut:
    channel_name, _, menu_path = channel_info(rec.type_id, rec.zone)
    s = _summary(rec)
    if rec.status == "resolved":
        result_note = RESULT_LABEL.get(rec.result or "", "")
    else:
        result_note = "결과를 기다리고 있어요"
    timeline = [
        TimelineEntry(key="input", label="상황 입력", note=_fmt_kst(rec.created_at), done=True),
        TimelineEntry(key="evidence", label="증거 준비", note=f"사진 {s.done_count}장 확인", done=s.complete),
        TimelineEntry(
            key="filed",
            label="접수 완료",
            note=f"{channel_name} > {menu_path[0]}",
            done=rec.status != "preparing",
        ),
        TimelineEntry(key="result", label="처리 결과", note=result_note, done=rec.status == "resolved"),
    ]
    return ReportOut(
        id=rec.id,
        analysis_id=rec.analysis_id,
        sequence=rec.sequence,
        total=rec.total,
        type_id=rec.type_id,
        category=rec.category,
        label=rec.label,
        status=rec.status,
        status_label=_status_label(rec),
        location=rec.location,
        created_at=rec.created_at,
        evidence_progress=EvidenceProgress(done=s.done_count, required=s.required_count),
        current_step=rec.current_step,
        step_count=STEP_COUNT,
        channel=ReportChannel(name=channel_name, menu_path=menu_path),
        photos=_report_photos(session, rec),
        draft_text=rec.draft_text,
        receipt_number=rec.receipt_number,
        filed_at=rec.filed_at,
        result=rec.result,
        result_reason=rec.result_reason,
        resolved_at=rec.resolved_at,
        timeline=timeline,
        case_id=case_service.case_id_for_report(session, rec.id),
        next_report_id=_next_report_id(session, rec),
    )


def list_reports(session: Session, device_id: str, status: str | None, limit: int, cursor: str | None) -> ReportList:
    try:
        offset = int(cursor) if cursor else 0
        if offset < 0:
            raise ValueError
    except ValueError:
        raise validation_error("'cursor' 값을 확인해 주세요.") from None

    stmt = select(Report).where(Report.device_id == device_id)
    if status:
        stmt = stmt.where(Report.status == status)
    # 최신순, 같은 시각이면 진행 순서
    stmt = stmt.order_by(Report.created_at.desc(), Report.sequence, Report.id)  # type: ignore[attr-defined]
    rows = session.exec(stmt.offset(offset).limit(limit + 1)).all()
    page, has_more = rows[:limit], len(rows) > limit

    items = []
    for r in page:
        photos = _report_photos(session, r)
        items.append(
            ReportListItem(
                id=r.id,
                type_id=r.type_id,
                category=r.category,
                label=r.label,
                status=r.status,
                status_label=_status_label(r),
                district=r.district,
                dong=r.dong,
                created_at=r.created_at,
                thumbnail_url=photos[0].url if photos else None,
                resumable=r.status == "preparing",
            )
        )
    return ReportList(items=items, next_cursor=str(offset + limit) if has_more else None)


def patch_report(session: Session, rec: Report, patch: ReportPatch) -> ReportOut:
    fields = patch.model_fields_set
    new_status = rec.status

    # 1) 검증만 먼저 하고, 통과하면 한 번에 반영합니다.
    if patch.status == "filed":
        if rec.status != "preparing":
            raise invalid_state("이미 접수한 건이에요. 진행 단계를 거꾸로 바꿀 수 없어요.")
        if not _summary(rec).complete:
            raise invalid_state("필요한 증거를 모두 준비한 뒤에 접수 완료로 바꿀 수 있어요.")
        new_status = "filed"
    if patch.result is not None:
        if new_status == "preparing":
            raise invalid_state("접수를 마친 뒤에 처리 결과를 입력할 수 있어요.")
        if patch.result == "unknown" and rec.status == "resolved":
            raise invalid_state("처리 완료된 건은 '아직 몰라요'로 되돌릴 수 없어요.")
        if patch.result in ("accepted", "rejected"):
            new_status = "resolved"

    # 2) 반영
    now = now_kst()
    if patch.current_step is not None:
        rec.current_step = patch.current_step
    if "receipt_number" in fields:
        rec.receipt_number = patch.receipt_number
    if "result_reason" in fields:
        rec.result_reason = patch.result_reason
    if patch.result is not None:
        rec.result = patch.result
    if new_status != rec.status:
        if new_status == "filed":
            rec.filed_at = now
        if new_status == "resolved":
            rec.resolved_at = now
        rec.status = new_status
    session.add(rec)
    session.commit()
    return report_out(session, rec)


# ---------- 접수 안내 ----------
def _guide_steps(session: Session, rec: Report, t: TypeDef) -> list[GuideStep]:
    skip = rec.sequence >= 2  # 앞 건에서 끝낸 접속·로그인·위치는 건너뜁니다.
    photos = [PhotoRef(id=p.id, url=p.url) for p in _report_photos(session, rec)]
    menu = " > ".join(t.menu_path)

    if t.capture_in_app:
        photo_step = GuideStep(
            order=4,
            step_id="attach_photos",
            title=f"사진 항목에 아래 {len(photos)}장을 첨부하세요" if photos else "사진 항목에 사진을 첨부하세요",
            body="사진을 먼저 저장한 뒤 안전신문고에서 골라 주세요.",
            action=GuideAction(kind="save_photos", button_label="사진 저장", photos=photos),
            skipped=False,
            verified=False,
        )
    else:  # 불법주정차는 본촬영 사진을 안전신문고 앱에서 직접 찍습니다.
        photo_step = GuideStep(
            order=4,
            step_id="attach_photos",
            title="안전신문고 앱에서 사진 2장을 찍으세요",
            body="같은 위치, 같은 방향에서 1분 간격으로 찍어요. 앞에서 1장, 옆에서 1장은 반려돼요.",
            action=GuideAction(kind="confirm", button_label="했어요"),
            skipped=False,
            verified=False,
        )

    return [
        GuideStep(
            order=1,
            step_id="open_site",
            title="안전신문고에 접속하세요",
            body="safetyreport.go.kr 또는 안전신문고 앱을 열어요.",
            action=GuideAction(kind="open_link", button_label="안전신문고 열기", url=WEB_URL),
            skipped=skip,
            verified=False,
        ),
        GuideStep(
            order=2,
            step_id="login",
            title="안전신문고에 로그인하세요",
            body="로그인은 한 번만 하면 돼요.",
            action=GuideAction(kind="confirm", button_label="했어요"),
            skipped=skip,
            verified=False,
        ),
        GuideStep(
            order=3,
            step_id="select_menu",
            title="메뉴를 아래 순서로 선택하세요",
            body=menu,
            action=GuideAction(kind="confirm", button_label="했어요"),
            skipped=False,
            verified=False,
        ),
        photo_step,
        GuideStep(
            order=5,
            step_id="set_location",
            title="위치를 확인하세요",
            body=rec.location.address or "사진 속 장소를 지도에서 골라 주세요.",
            action=GuideAction(kind="confirm", button_label="했어요"),
            skipped=skip,
            verified=False,
        ),
        GuideStep(
            order=6,
            step_id="fill_content",
            title="내용 항목에 아래 글을 붙여 넣으세요",
            body=None,
            action=GuideAction(kind="copy_text", button_label="글 복사", text=rec.draft_text),
            skipped=False,
            verified=False,
        ),
        GuideStep(
            order=7,
            step_id="submit",
            title="접수 버튼을 눌러 마무리하세요",
            body="접수번호가 나오면 적어 두세요. 내 신고에서 입력할 수 있어요.",
            action=GuideAction(kind="submit", button_label="접수 완료"),
            skipped=False,
            verified=False,
        ),
    ]


def guide_out(session: Session, rec: Report) -> GuideOut:
    t = type_def(rec.type_id)
    channel_name, web_url, menu_path = channel_info(rec.type_id, rec.zone)
    carry_over: list[CarryOver] = []
    if rec.sequence >= 2:
        carry_over = [
            CarryOver(label="안전신문고 로그인", message="이미 하셨어요, 건너뛰어요"),
            CarryOver(label="위치 확인", message="같은 장소라 그대로 써요"),
            CarryOver(
                label="사진",
                message=(
                    "이 건에 맞는 사진을 따로 준비했어요"
                    if t.capture_in_app
                    else "안전신문고 앱에서 새로 찍어야 해요"
                ),
            ),
        ]
    if is_mock():
        steps = _guide_steps(session, rec, t)
    else:  # 실제 모드: 제목, 메뉴 경로, 버튼은 절차 데이터에서 그대로 가져옵니다.
        steps = procedure_guide.build_steps(
            procedures.get_procedure(rec.type_id),
            skip_reusable=rec.sequence >= 2,
            photos=[PhotoRef(id=p.id, url=p.url) for p in _report_photos(session, rec)],
            menu_path=menu_path,
            address=rec.location.address,
            draft_text=rec.draft_text,
        )
    return GuideOut(
        report_id=rec.id,
        label=rec.label,
        sequence=rec.sequence,
        total=rec.total,
        channel=GuideChannel(name=channel_name, web_url=web_url, menu_path=menu_path),
        current_step=rec.current_step,
        carry_over=carry_over,
        steps=steps,
    )


# ---------- 문구 ----------
def make_draft(session: Session, rec: Report, tone: str) -> DraftOut:
    text = fixtures.DRAFTS[(rec.type_id, tone)]
    rec.draft_text = text
    session.add(rec)
    session.commit()
    return DraftOut(text=text, tone=tone)
