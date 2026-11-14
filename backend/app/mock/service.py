"""가짜 API의 상태 전이와 응답 조립. AI·DB·S3를 부르지 않습니다."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import UploadFile

from app.errors import ApiError, ErrorCode, invalid_state, not_found, validation_error
from app.mock import fixtures
from app.mock.catalog import CATALOG, CHANNEL_NAME, WEB_URL, SceneDef, TypeDef
from app.mock.fixtures import PLACEHOLDER_URL
from app.mock.store import AnalysisRecord, ReportRecord, SceneState, store
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

KST = timezone(timedelta(hours=9))
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PHOTOS_PER_ANALYSIS = 4
RESULT_LABEL = {"accepted": "수용", "rejected": "불수용", "unknown": "아직 몰라요"}


def now_kst() -> datetime:
    return datetime.now(KST).replace(microsecond=0)


def new_id() -> str:
    return str(uuid4())


def _placeholder() -> PhotoRef:
    return PhotoRef(id=new_id(), url=PLACEHOLDER_URL)


# ---------- 업로드 검사 (파일은 저장하지 않고 버립니다) ----------
async def check_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME:
        raise ApiError(415, ErrorCode.UNSUPPORTED_MEDIA, "JPEG, PNG, WebP 사진만 올릴 수 있어요.")
    data = await file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise ApiError(413, ErrorCode.PHOTO_TOO_LARGE, "사진이 너무 커요. 10MB 이하로 올려 주세요.")


# ---------- 소유권 확인 ----------
def get_analysis_record(device_id: str, analysis_id: str) -> AnalysisRecord:
    rec = store.analyses.get(analysis_id)
    if rec is None or rec.device_id != device_id:
        raise not_found()
    return rec


def get_report_record(device_id: str, report_id: str) -> ReportRecord:
    rec = store.reports.get(report_id)
    if rec is None or rec.device_id != device_id:
        raise not_found()
    return rec


# ---------- 분석 ----------
def create_analysis(device_id: str, text: str | None, photo_count: int) -> AnalysisResponse:
    analysis_id = new_id()
    photos = [_placeholder() for _ in range(photo_count)]
    response = fixtures.build_analysis(analysis_id, now_kst(), text, photos)
    store.analyses[analysis_id] = AnalysisRecord(analysis_id, device_id, response)
    return response


def create_reports(device_id: str, analysis_id: str, type_ids: list[str]) -> CreateReportsResponse:
    analysis = get_analysis_record(device_id, analysis_id).response
    available = {item.type_id: item for item in analysis.items}
    if len(set(type_ids)) != len(type_ids):
        raise validation_error("같은 항목이 두 번 들어 있어요.")
    if any(t not in available for t in type_ids):
        raise validation_error("분석 결과에 없는 항목이에요.")
    if any(r.analysis_id == analysis_id for r in store.reports.values()):
        raise invalid_state("이미 신고 건을 만들었어요. 내 신고에서 이어서 해 주세요.")

    created_at = now_kst()
    first_photo = analysis.input.photos[0] if analysis.input.photos else None
    created: list[CreatedReport] = []
    for seq, type_id in enumerate(type_ids, start=1):
        item = available[type_id]
        scenes: dict[str, SceneState] = {}
        for scene in CATALOG[type_id].scenes:
            state = SceneState()
            if scene.prefill_from_analysis and first_photo:  # 분석 사진 재사용 (AI 재호출 없음)
                state.photo = first_photo
                state.review = SceneReview(status="sufficient", message=scene.sufficient_message)
            scenes[scene.scene_id] = state
        rec = ReportRecord(
            id=new_id(),
            device_id=device_id,
            analysis_id=analysis_id,
            type_id=type_id,
            category=item.category,
            label=item.label,
            sequence=seq,
            total=len(type_ids),
            location=analysis.location,
            created_at=created_at,
            scenes=scenes,
        )
        store.reports[rec.id] = rec
        created.append(CreatedReport(id=rec.id, type_id=type_id, sequence=seq, status="preparing"))
    return CreateReportsResponse(analysis_id=analysis_id, total=len(created), reports=created)


# ---------- 증거 ----------
def _scene_defs(rec: ReportRecord) -> tuple[SceneDef, ...]:
    return CATALOG[rec.type_id].scenes


def _summary(rec: ReportRecord) -> EvidenceSummary:
    required = len(_scene_defs(rec))
    done = sum(1 for s in rec.scenes.values() if s.review and s.review.status == "sufficient")
    return EvidenceSummary(required_count=required, done_count=done, complete=done >= required)


def _report_photos(rec: ReportRecord) -> list[ScenePhoto]:
    photos = [
        ScenePhoto(id=s.photo.id, url=s.photo.url, scene_id=scene_id)
        for scene_id, s in rec.scenes.items()
        if s.photo
    ]
    return photos + rec.extra_photos


def evidence_out(rec: ReportRecord) -> EvidenceOut:
    summary = _summary(rec)
    remaining = summary.required_count - summary.done_count
    intro = (
        f"{rec.label}부터 준비할게요. 사진이 {remaining}장 더 필요해요."
        if remaining
        else f"{rec.label} 사진이 모두 준비됐어요."
    )
    if not CATALOG[rec.type_id].capture_in_app:
        intro = f"{rec.label}은 사전 점검으로 확인해요. 본촬영은 안전신문고 앱에서 해요."
    scenes = [
        EvidenceScene(
            scene_id=d.scene_id,
            label=d.label,
            required=True,
            photo=rec.scenes[d.scene_id].photo,
            review=rec.scenes[d.scene_id].review,
        )
        for d in _scene_defs(rec)
    ]
    return EvidenceOut(
        report_id=rec.id,
        label=rec.label,
        intro=intro,
        capture_in_app=CATALOG[rec.type_id].capture_in_app,
        scenes=scenes,
        **summary.model_dump(),
    )


def upload_photo(rec: ReportRecord, scene_id: str | None) -> PhotoUploadOut:
    photo = ScenePhoto(id=new_id(), url=PLACEHOLDER_URL, scene_id=scene_id)
    review: SceneReview | None = None
    if scene_id is None:  # 검수하지 않고 보관만 합니다.
        rec.extra_photos.append(photo)
    else:
        scene = next((d for d in _scene_defs(rec) if d.scene_id == scene_id), None)
        if scene is None:
            raise validation_error("알 수 없는 장면이에요.")
        state = rec.scenes[scene_id]
        state.attempts += 1
        state.photo = PhotoRef(id=photo.id, url=photo.url)  # 같은 장면은 이전 사진을 대체
        if state.attempts >= 2:  # 재촬영 시연: 첫 업로드는 불충분, 두 번째부터 충분
            review = SceneReview(status="sufficient", message=scene.sufficient_message)
        else:
            review = SceneReview(
                status="insufficient", message=scene.insufficient_message, retake_tip=scene.retake_tip
            )
        state.review = review
    return PhotoUploadOut(photo=photo, review=review, evidence=_summary(rec))


def rehearsal(device_id: str, rec: ReportRecord, photo_id: str | None) -> RehearsalOut:
    if rec.type_id != "illegal_parking":
        raise invalid_state("불법주정차 건에서만 사전 점검을 할 수 있어요.")
    analysis = get_analysis_record(device_id, rec.analysis_id).response
    known = {p.id: p for p in analysis.input.photos}
    known.update({p.id: PhotoRef(id=p.id, url=p.url) for p in _report_photos(rec)})
    if photo_id is not None and photo_id not in known:
        raise not_found()
    photo = known.get(photo_id) if photo_id else (analysis.input.photos[0] if analysis.input.photos else None)

    scene = _scene_defs(rec)[0]  # 사전 점검을 본 것만으로 증거 단계 완료 (명세 5장)
    state = rec.scenes[scene.scene_id]
    state.photo = photo
    state.review = SceneReview(status="sufficient", message=scene.sufficient_message)

    item = next(i for i in analysis.items if i.type_id == "illegal_parking")
    return fixtures.build_rehearsal(str(item.detail.get("zone", "sidewalk")))


# ---------- 신고 건 ----------
def _status_label(rec: ReportRecord) -> str:
    if rec.status == "preparing":
        s = _summary(rec)
        return f"준비 중 · 증거 {s.done_count}/{s.required_count}"
    if rec.status == "filed":
        return "접수 완료"
    return f"처리 완료 · {RESULT_LABEL.get(rec.result or '', '')}"


def _fmt_kst(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    return f"{dt.month}월 {dt.day}일 {'오전' if dt.hour < 12 else '오후'} {hour12}:{dt.minute:02d}"


def _next_report_id(rec: ReportRecord) -> str | None:
    later = [
        r
        for r in store.reports.values()
        if r.analysis_id == rec.analysis_id and r.sequence > rec.sequence and r.status == "preparing"
    ]
    return min(later, key=lambda r: r.sequence).id if later else None


def report_out(rec: ReportRecord) -> ReportOut:
    t = CATALOG[rec.type_id]
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
            note=f"{CHANNEL_NAME} > {t.menu_path[0]}",
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
        channel=ReportChannel(name=CHANNEL_NAME, menu_path=list(t.menu_path)),
        photos=_report_photos(rec),
        draft_text=rec.draft_text,
        receipt_number=rec.receipt_number,
        filed_at=rec.filed_at,
        result=rec.result,
        result_reason=rec.result_reason,
        resolved_at=rec.resolved_at,
        timeline=timeline,
        case_id=None,  # 사례 공유는 이번 범위가 아닙니다.
        next_report_id=_next_report_id(rec),
    )


def list_reports(device_id: str, status: str | None, limit: int, cursor: str | None) -> ReportList:
    try:
        offset = int(cursor) if cursor else 0
        if offset < 0:
            raise ValueError
    except ValueError:
        raise validation_error("'cursor' 값을 확인해 주세요.") from None

    mine = [r for r in store.reports.values() if r.device_id == device_id]
    if status:
        mine = [r for r in mine if r.status == status]
    mine.sort(key=lambda r: (-r.created_at.timestamp(), r.sequence))  # 최신순, 같은 시각이면 진행 순서
    page = mine[offset : offset + limit]
    items = [
        ReportListItem(
            id=r.id,
            type_id=r.type_id,
            category=r.category,
            label=r.label,
            status=r.status,
            status_label=_status_label(r),
            district=r.location.district,
            dong=r.location.dong,
            created_at=r.created_at,
            thumbnail_url=(_report_photos(r)[0].url if _report_photos(r) else None),
            resumable=r.status == "preparing",
        )
        for r in page
    ]
    next_cursor = str(offset + limit) if offset + limit < len(mine) else None
    return ReportList(items=items, next_cursor=next_cursor)


def patch_report(rec: ReportRecord, patch: ReportPatch) -> ReportOut:
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
    return report_out(rec)


# ---------- 접수 안내 ----------
def _guide_steps(rec: ReportRecord, t: TypeDef) -> list[GuideStep]:
    skip = rec.sequence >= 2  # 앞 건에서 끝낸 접속·로그인·위치는 건너뜁니다.
    photos = [PhotoRef(id=p.id, url=p.url) for p in _report_photos(rec)]
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


def guide_out(rec: ReportRecord) -> GuideOut:
    t = CATALOG[rec.type_id]
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
    return GuideOut(
        report_id=rec.id,
        label=rec.label,
        sequence=rec.sequence,
        total=rec.total,
        channel=GuideChannel(name=CHANNEL_NAME, web_url=WEB_URL, menu_path=list(t.menu_path)),
        current_step=rec.current_step,
        carry_over=carry_over,
        steps=_guide_steps(rec, t),
    )


# ---------- 문구 ----------
def make_draft(rec: ReportRecord, tone: str) -> DraftOut:
    text = fixtures.DRAFTS[(rec.type_id, tone)]
    rec.draft_text = text
    return DraftOut(text=text, tone=tone)
