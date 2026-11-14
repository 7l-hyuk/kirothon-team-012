"""SQLModel 테이블: analyses, reports, photos, ai_usage.

- PostgreSQL 전용 타입(JSONB, ARRAY)은 쓰지 않습니다. 테스트가 SQLite로 돌기 때문입니다.
- 깊은 구조의 값은 `sqlalchemy.JSON` 컬럼에 둡니다.
- 사진 URL은 저장하지 않습니다. `photos.s3_key`만 두고 응답을 만들 때 URL을 만듭니다.
- 시각은 KSTDateTime(저장은 UTC, 읽을 때 KST).
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Column, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.types import KSTDateTime
from app.schemas.common import Location
from app.timeutil import now_kst


def _dt(*, nullable: bool = False, default: bool = True, on_update: bool = False) -> Any:
    """시각 컬럼. Column 객체는 테이블마다 새로 만들어야 해서 함수로 둡니다."""
    kwargs: dict[str, Any] = {}
    if default:
        kwargs["default"] = now_kst
    if on_update:
        kwargs["onupdate"] = now_kst
    column = Column(KSTDateTime(), nullable=nullable, **kwargs)
    if default:
        return Field(default_factory=now_kst, sa_column=column)
    return Field(default=None, sa_column=column)


def _json(default_factory: Any = dict) -> Any:
    return Field(default_factory=default_factory, sa_column=Column(JSON, nullable=False))


class Analysis(SQLModel, table=True):
    __tablename__ = "analyses"

    id: str = Field(primary_key=True, max_length=36)
    device_id: str = Field(index=True, max_length=36)
    situation_text: str | None = None
    # AnalysisResponse에서 id, created_at, input(사진 URL 포함)을 뺀 나머지. 사진은 photos 테이블에서 읽습니다.
    result: dict[str, Any] = _json()
    # 분석 때 올린 사진이 이미 충족한 증거 장면: {type_id: [{scene_id, photo_id, message}]}
    scene_matches: dict[str, Any] = _json()
    # 문제가 보이는 사진 ID: {type_id: [photo_id]}
    item_photo_ids: dict[str, Any] = _json()
    address: str | None = None
    district: str | None = None
    dong: str | None = None
    created_at: datetime = _dt()


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("analysis_id", "sequence", name="uq_reports_analysis_sequence"),)

    id: str = Field(primary_key=True, max_length=36)
    device_id: str = Field(index=True, max_length=36)
    analysis_id: str = Field(
        sa_column=Column(String(36), ForeignKey("analyses.id"), nullable=False, index=True)
    )
    type_id: str
    category: str
    label: str
    sequence: int
    total: int
    status: str = "preparing"  # preparing / filed / resolved
    current_step: int = 0
    situation_text: str | None = None
    location_text: str | None = None  # 위치의 address
    district: str | None = None
    dong: str | None = None
    summary: str | None = None
    zone: str | None = None  # 불법주정차 구역(분석 또는 사전 점검 결과)
    draft_text: str | None = None
    receipt_number: str | None = None
    result: str | None = None  # accepted / rejected / unknown
    result_reason: str | None = None
    # 증거 장면별 상태: {scene_id: {photo_id, review, attempts}}. 같은 사진이 여러 건의 장면에 쓰일 수 있어 건에 둡니다.
    scenes: dict[str, Any] = _json()
    filed_at: datetime | None = _dt(nullable=True, default=False)
    resolved_at: datetime | None = _dt(nullable=True, default=False)
    created_at: datetime = _dt()
    updated_at: datetime = _dt(on_update=True)

    @property
    def location(self) -> Location:
        return Location(address=self.location_text, district=self.district, dong=self.dong)


class Photo(SQLModel, table=True):
    __tablename__ = "photos"

    id: str = Field(primary_key=True, max_length=36)
    device_id: str = Field(index=True, max_length=36)
    analysis_id: str | None = Field(
        default=None, sa_column=Column(String(36), ForeignKey("analyses.id"), nullable=True, index=True)
    )
    report_id: str | None = Field(
        default=None, sa_column=Column(String(36), ForeignKey("reports.id"), nullable=True, index=True)
    )
    # 저장소 키. 가짜 모드의 자리표시 사진은 파일이 없어 None입니다.
    s3_key: str | None = None
    scene_id: str | None = None
    # 업로드 때 받은 검수 결과 기록. 증거 장면의 현재 상태는 reports.scenes가 기준입니다.
    review_status: str | None = None
    review_message: str | None = None
    retake_tip: str | None = None
    taken_order: int = 1
    created_at: datetime = _dt()


class AiUsage(SQLModel, table=True):
    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("device_id", "day", name="uq_ai_usage_device_day"),)

    id: int | None = Field(default=None, primary_key=True)
    device_id: str = Field(max_length=36)
    day: date  # KST 날짜
    count: int = 0
