"""상황 분석과 신고 건 생성 (명세 3장)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Category, Location, PhotoRef, ReportStatus, TypeId


class AnalysisInput(BaseModel):
    text: str | None = None
    photos: list[PhotoRef] = []


class AnalysisItem(BaseModel):
    type_id: TypeId
    category: Category
    label: str
    subtitle: str
    reason: str
    detail: dict[str, Any] = {}


class UnsupportedItem(BaseModel):
    label: str
    message: str


class NotReportable(BaseModel):
    title: str
    message: str
    basis: str


class AnalysisResponse(BaseModel):
    id: str
    created_at: datetime
    input: AnalysisInput
    reportable: bool
    summary: str
    items: list[AnalysisItem]
    unsupported_items: list[UnsupportedItem]
    not_reportable: NotReportable | None
    location: Location
    emergency: bool
    disclaimer: str


class CreateReportsRequest(BaseModel):
    type_ids: list[TypeId] = Field(min_length=1)


class CreatedReport(BaseModel):
    id: str
    type_id: TypeId
    sequence: int
    status: ReportStatus


class CreateReportsResponse(BaseModel):
    analysis_id: str
    total: int
    reports: list[CreatedReport]
