"""AI 구조화 출력 모델. client.messages.parse(output_format=...)에 넘깁니다.

규칙: 모든 필드는 필수이고, 값이 없을 수 있으면 `X | None`으로 선언합니다. 열거형은 Literal입니다.
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ReviewStatus, TypeId, Zone


# ---- 상황 분석 ----
class SceneMatchOut(BaseModel):
    scene_id: str  # 절차 데이터의 evidence_scenes[].scene_id
    photo_number: int  # 이 장면을 충족하는 사진 번호 (1부터)
    message: str  # 왜 충분한지 한 줄 (해요체)


class AnalysisItemOut(BaseModel):
    type_id: TypeId
    label: str  # AI가 본 문제 이름. 목록 밖 유형일 때 안내 문구에 씁니다.
    reason: str  # 왜 신고가 되는지 (해요체, 한두 문장)
    zone: Zone | None  # 불법주정차만
    satisfied_scenes: list[SceneMatchOut]
    photo_numbers: list[int]  # 이 문제가 보이는 사진 번호 (1부터). 보이는 사진이 없으면 빈 목록


class UnsupportedItemOut(BaseModel):
    label: str


class NotReportableOut(BaseModel):
    message: str  # 신고가 어려운 이유와 권유 (해요체)
    basis: str  # 근거 (해요체)


class LocationOut(BaseModel):
    address: str | None
    district: str | None
    dong: str | None


class AnalysisOutput(BaseModel):
    summary: str
    items: list[AnalysisItemOut]
    unsupported_items: list[UnsupportedItemOut]
    not_reportable: NotReportableOut | None
    location: LocationOut
    emergency: bool


# ---- 증거 검수 ----
class ReviewOutput(BaseModel):
    status: ReviewStatus
    message: str
    retake_tip: str | None


# ---- 불법주정차 사전 점검 ----
class RehearsalOutput(BaseModel):
    zone: Zone | None  # 6대 금지구역 중 어디인지. 아니면 null
    zone_status: ReviewStatus
    zone_detail: str | None
    plate_readable: ReviewStatus
    plate_detail: str | None
    background_included: ReviewStatus
    background_detail: str | None


# ---- 문구 대필 ----
class DraftOutput(BaseModel):
    text: str


Tone = Literal["default", "shorter", "politer"]
