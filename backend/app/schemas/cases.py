"""사례 공유와 사례 (명세 7, 8장). CaseFacts는 AI에 넘기는 자료입니다."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, StrictBool

from app.schemas.common import PhotoRef, TypeId


# ---- 7장: 사례 공유 ----
class CaseSection(BaseModel):
    heading: str
    body: str


class RemovedItem(BaseModel):
    label: str
    treatment: str


class CasePreview(BaseModel):
    title: str
    type_id: TypeId
    result_label: str
    district: str | None
    period: str
    sections: list[CaseSection]
    photos: list[PhotoRef]
    removed: list[RemovedItem]
    photo_notice: str


class CaseShareRequest(BaseModel):
    consent: StrictBool


# ---- 8장: 사례 ----
class CaseSectionDetail(CaseSection):
    photos: list[PhotoRef]


class CaseDetail(BaseModel):
    id: str
    title: str
    type_id: TypeId
    type_label: str
    result_label: str
    district: str | None
    period: str
    sections: list[CaseSectionDetail]
    like_count: int
    liked_by_me: bool
    is_mine: bool
    created_at: datetime


class CaseListItem(BaseModel):
    id: str
    title: str
    type_id: TypeId
    type_label: str
    result_label: str
    district: str | None
    like_count: int
    cover_url: str | None


class CaseList(BaseModel):
    items: list[CaseListItem]
    next_cursor: str | None


class LikeOut(BaseModel):
    like_count: int
    liked_by_me: bool


# ---- AI에 넘기는 자료. 상세 주소, 접수번호, 일(day)이 든 날짜는 들어가지 않습니다. ----
class EvidenceFact(BaseModel):
    label: str
    required: bool
    status: Literal["sufficient", "insufficient", "undetermined"]
    message: str | None


class RehearsalFact(BaseModel):
    """불법주정차 사전 점검 항목 하나의 실제 판정."""

    label: str
    status: Literal["sufficient", "insufficient", "undetermined"]


class CaseFacts(BaseModel):
    type_id: TypeId
    label: str  # 신고 건 라벨. 예: "불법주정차 (인도)"
    kind: Literal["신고", "민원"]
    zone_label: str | None
    summary: str  # 분석 요약(scrub 적용)
    district: str | None
    period: str
    photo_count: int
    evidence: list[EvidenceFact]
    rehearsal_done: bool = False  # 사전 점검을 거쳤는가(결과를 모를 수 있음)
    rehearsal: list[RehearsalFact] = []  # 저장된 항목별 판정. 비어 있으면 결과를 모르는 것
    agency: str | None
    channel_name: str
    menu_path: list[str]  # 절차 데이터가 verified일 때만 채웁니다. 아니면 빈 목록
    capture_note: str | None  # 불법주정차 촬영 규칙 한 줄(절차 데이터에서 조립)
    capture_warning: str | None
    tips: list[str]  # 절차 데이터의 재촬영 안내와 통과 기준
    filed: bool
    result: Literal["accepted", "rejected", "pending"]
    result_label: str
    result_reason: str | None  # scrub 적용
