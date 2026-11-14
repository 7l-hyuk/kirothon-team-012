"""사례 공유와 사례 API (S11, S12~S14). 검증과 응답 변환만 하고 로직은 services/cases.py에 둡니다.

공유·미리보기·내리기는 내 신고 건에 대한 요청이라 기기 ID로 건을 찾습니다(다른 기기의 건은 404).
사례 조회(`/api/cases`)는 누구나 볼 수 있고, 기기 ID는 `liked_by_me`, `is_mine` 계산에만 씁니다.
미리보기는 AI를 부를 수 있어(처음 한 번) 기기당 하루 상한에 포함됩니다.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import DeviceId, SessionDep
from app.schemas.cases import (
    CaseDetail,
    CaseList,
    CasePreview,
    CaseShareRequest,
    LikeOut,
)
from app.schemas.common import TypeId
from app.services import cases

router = APIRouter(prefix="/api", tags=["cases"])


# ---- 내 신고 건의 사례 공유 (7장) ----
@router.get("/reports/{report_id}/case-preview", response_model=CasePreview)
def case_preview(report_id: str, device_id: DeviceId, session: SessionDep) -> CasePreview:
    return cases.preview(session, device_id, report_id)


@router.post("/reports/{report_id}/case", status_code=201, response_model=CaseDetail)
def share_case(report_id: str, body: CaseShareRequest, device_id: DeviceId, session: SessionDep) -> CaseDetail:
    return cases.share(session, device_id, report_id, body.consent)


@router.delete("/reports/{report_id}/case", status_code=204)
def unshare_case(report_id: str, device_id: DeviceId, session: SessionDep) -> None:
    cases.unshare(session, device_id, report_id)


# ---- 사례 (8장) ----
@router.get("/cases", response_model=CaseList)
def list_cases(
    device_id: DeviceId,  # 헤더 검사만 합니다. 목록은 기기와 무관해요.
    session: SessionDep,
    type_filter: Annotated[TypeId | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> CaseList:
    return cases.list_cases(session, type_filter, limit, cursor)


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, device_id: DeviceId, session: SessionDep) -> CaseDetail:
    return cases.get_case(session, device_id, case_id)


@router.put("/cases/{case_id}/like", response_model=LikeOut)
def like_case(case_id: str, device_id: DeviceId, session: SessionDep) -> LikeOut:
    return cases.like(session, device_id, case_id)


@router.delete("/cases/{case_id}/like", response_model=LikeOut)
def unlike_case(case_id: str, device_id: DeviceId, session: SessionDep) -> LikeOut:
    return cases.unlike(session, device_id, case_id)
