"""분석 API (S1~S3). 검증과 응답 변환만 하고 로직은 services에 둡니다.

`ANTHROPIC_API_KEY`가 없으면 가짜 응답(app.mock.service), 있으면 Claude 호출(app.services.assist)입니다.
어느 쪽이든 결과는 DB에 저장합니다. 엔드포인트는 모두 `def`라서 스레드풀에서 돌고, 이벤트 루프를 막지 않습니다.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.config import is_mock
from app.deps import DeviceId, SessionDep
from app.errors import validation_error
from app.mock import service
from app.schemas.analyses import (
    AnalysisResponse,
    CreateReportsRequest,
    CreateReportsResponse,
)
from app.services import assist

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

MAX_TEXT_LENGTH = 500
MAX_ADDRESS_LENGTH = 200


@router.post("", status_code=201, response_model=AnalysisResponse)
def create_analysis(
    device_id: DeviceId,
    session: SessionDep,
    text: Annotated[str | None, Form()] = None,
    address: Annotated[str | None, Form()] = None,  # 가짜 모드에서는 쓰지 않습니다.
    photos: Annotated[list[UploadFile] | None, File()] = None,
) -> AnalysisResponse:
    text = (text or "").strip() or None
    address = (address or "").strip() or None
    # 브라우저는 사진이 없어도 파일명이 빈 파트를 보낼 수 있어 걸러냅니다.
    files = [p for p in (photos or []) if p.filename]

    if text is None and not files:
        raise validation_error("사진이나 글을 하나 이상 알려 주세요.")
    if text and len(text) > MAX_TEXT_LENGTH:
        raise validation_error("상황 설명은 500자 이하로 적어 주세요.")
    if address and len(address) > MAX_ADDRESS_LENGTH:
        raise validation_error("위치는 200자 이하로 적어 주세요.")
    if len(files) > service.MAX_PHOTOS_PER_ANALYSIS:
        raise validation_error("사진은 최대 4장까지 올릴 수 있어요.")

    if is_mock():
        for f in files:
            service.check_upload(f)
        return service.create_analysis(session, device_id, text, len(files))
    return assist.create_analysis(session, device_id, text, address, files)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, device_id: DeviceId, session: SessionDep) -> AnalysisResponse:
    return service.get_analysis_record(session, device_id, analysis_id).response


@router.post("/{analysis_id}/reports", status_code=201, response_model=CreateReportsResponse)
def create_reports(
    analysis_id: str, body: CreateReportsRequest, device_id: DeviceId, session: SessionDep
) -> CreateReportsResponse:
    return service.create_reports(session, device_id, analysis_id, list(body.type_ids))
