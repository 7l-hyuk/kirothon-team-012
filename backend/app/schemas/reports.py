"""신고 건, 증거, 사전 점검, 접수 안내, 문구 (명세 4~6장)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import (
    Category,
    Location,
    PhotoRef,
    ReportStatus,
    ResultValue,
    ReviewStatus,
    ScenePhoto,
    TypeId,
)

STEP_COUNT = 7  # 접수 안내 단계 수


# ---- 신고 건 ----
class ReportChannel(BaseModel):
    name: str
    menu_path: list[str]


class EvidenceProgress(BaseModel):
    done: int
    required: int


class TimelineEntry(BaseModel):
    key: str
    label: str
    note: str
    done: bool


class ReportOut(BaseModel):
    id: str
    analysis_id: str
    sequence: int
    total: int
    type_id: TypeId
    category: Category
    label: str
    status: ReportStatus
    status_label: str
    location: Location
    created_at: datetime
    evidence_progress: EvidenceProgress
    current_step: int
    step_count: int
    channel: ReportChannel
    photos: list[ScenePhoto]
    draft_text: str | None
    receipt_number: str | None
    filed_at: datetime | None
    result: ResultValue | None
    result_reason: str | None
    resolved_at: datetime | None
    timeline: list[TimelineEntry]
    case_id: str | None
    next_report_id: str | None


class ReportListItem(BaseModel):
    id: str
    type_id: TypeId
    category: Category
    label: str
    status: ReportStatus
    status_label: str
    district: str | None
    dong: str | None
    created_at: datetime
    thumbnail_url: str | None
    resumable: bool


class ReportList(BaseModel):
    items: list[ReportListItem]
    next_cursor: str | None


class ReportPatch(BaseModel):
    current_step: int | None = Field(default=None, ge=0, le=STEP_COUNT)
    status: Literal["filed"] | None = None
    receipt_number: str | None = Field(default=None, max_length=50)
    result: ResultValue | None = None
    result_reason: str | None = Field(default=None, max_length=300)


# ---- 증거 ----
class SceneReview(BaseModel):
    status: ReviewStatus
    message: str
    retake_tip: str | None = None


class EvidenceScene(BaseModel):
    scene_id: str
    label: str
    required: bool
    photo: PhotoRef | None
    review: SceneReview | None


class EvidenceSummary(BaseModel):
    required_count: int
    done_count: int
    complete: bool


class EvidenceOut(EvidenceSummary):
    report_id: str
    label: str
    intro: str
    capture_in_app: bool
    scenes: list[EvidenceScene]


class PhotoUploadOut(BaseModel):
    photo: ScenePhoto
    review: SceneReview | None
    evidence: EvidenceSummary


# ---- 사전 점검 ----
class RehearsalRequest(BaseModel):
    photo_id: str | None = None


class RehearsalCheck(BaseModel):
    key: Literal["zone", "plate_readable", "background_included"]
    status: ReviewStatus
    label: str
    detail: str | None


class CaptureGuide(BaseModel):
    title: str
    steps: list[str]
    warning: str
    interval_seconds: int
    interval_note: str


class RehearsalOut(BaseModel):
    passed: bool
    zone: str
    checks: list[RehearsalCheck]
    capture_guide: CaptureGuide


# ---- 접수 안내 ----
class GuideAction(BaseModel):
    kind: Literal["open_link", "confirm", "save_photos", "copy_text", "submit"]
    button_label: str
    url: str | None = None
    photos: list[PhotoRef] | None = None
    text: str | None = None


class GuideStep(BaseModel):
    order: int
    step_id: str
    title: str
    body: str | None
    action: GuideAction
    skipped: bool
    verified: bool


class GuideChannel(BaseModel):
    name: str
    web_url: str
    menu_path: list[str]


class CarryOver(BaseModel):
    label: str
    message: str


class GuideOut(BaseModel):
    report_id: str
    label: str
    sequence: int
    total: int
    channel: GuideChannel
    current_step: int
    carry_over: list[CarryOver]
    steps: list[GuideStep]


# ---- 문구 대필 ----
class DraftRequest(BaseModel):
    tone: Literal["default", "shorter", "politer"] = "default"


class DraftOut(BaseModel):
    text: str
    tone: Literal["default", "shorter", "politer"]
