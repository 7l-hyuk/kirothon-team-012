"""프로세스 메모리 저장소. 재시작하면 사라집니다."""

from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.analyses import AnalysisResponse
from app.schemas.common import Location, PhotoRef, ScenePhoto
from app.schemas.reports import SceneReview


@dataclass
class SceneState:
    photo: PhotoRef | None = None
    review: SceneReview | None = None
    attempts: int = 0  # 이 API로 올린 횟수. 1회차 불충분, 2회차부터 충분


@dataclass
class ReportRecord:
    id: str
    device_id: str
    analysis_id: str
    type_id: str
    category: str
    label: str
    sequence: int
    total: int
    location: Location
    created_at: datetime
    scenes: dict[str, SceneState]
    extra_photos: list[ScenePhoto] = field(default_factory=list)  # scene_id 없이 올린 사진
    status: str = "preparing"
    current_step: int = 0
    draft_text: str | None = None
    receipt_number: str | None = None
    filed_at: datetime | None = None
    result: str | None = None
    result_reason: str | None = None
    resolved_at: datetime | None = None


@dataclass
class AnalysisRecord:
    id: str
    device_id: str
    response: AnalysisResponse


class MockStore:
    def __init__(self) -> None:
        self.analyses: dict[str, AnalysisRecord] = {}
        self.reports: dict[str, ReportRecord] = {}

    def reset(self) -> None:
        self.analyses.clear()
        self.reports.clear()


store = MockStore()
