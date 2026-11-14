"""프로세스 메모리 저장소. 재시작하면 사라집니다. (DB 저장은 다음 Spec)"""

import threading
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.analyses import AnalysisResponse
from app.schemas.common import Location, PhotoRef, ScenePhoto
from app.schemas.reports import SceneReview


@dataclass
class SceneState:
    photo: PhotoRef | None = None
    review: SceneReview | None = None
    attempts: int = 0  # 가짜 모드에서만 씀. 1회차 불충분, 2회차부터 충분


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
    zone: str | None = None  # 불법주정차 구역(분석 또는 사전 점검 결과)
    status: str = "preparing"
    current_step: int = 0
    draft_text: str | None = None
    receipt_number: str | None = None
    filed_at: datetime | None = None
    result: str | None = None
    result_reason: str | None = None
    resolved_at: datetime | None = None


@dataclass
class SceneMatch:
    """분석 때 올린 사진이 이미 충족한 증거 장면. 신고 건을 만들 때 AI 재호출 없이 반영합니다."""

    scene_id: str
    photo_id: str
    message: str


@dataclass
class AnalysisRecord:
    id: str
    device_id: str
    response: AnalysisResponse
    scene_matches: dict[str, list[SceneMatch]] = field(default_factory=dict)  # type_id → 장면 목록
    item_photo_ids: dict[str, list[str]] = field(default_factory=dict)  # type_id → 그 문제가 보이는 사진 ID(번호순)


@dataclass
class PhotoRecord:
    id: str
    device_id: str
    data: bytes  # 긴 변 1568px 이하로 줄인 JPEG
    media_type: str = "image/jpeg"


class MemoryStore:
    def __init__(self) -> None:
        self.analyses: dict[str, AnalysisRecord] = {}
        self.reports: dict[str, ReportRecord] = {}
        self.photos: dict[str, PhotoRecord] = {}
        self.ai_usage: dict[tuple[str, str], int] = {}  # (기기 ID, KST 날짜) → 호출 수
        self.lock = threading.Lock()  # ai_usage 갱신용

    def reset(self) -> None:
        self.analyses.clear()
        self.reports.clear()
        self.photos.clear()
        self.ai_usage.clear()


store = MemoryStore()
