"""신고 건 API (S1, S4~S11). 검증과 응답 변환만 하고 로직은 services에 둡니다.

AI를 부르는 엔드포인트(photos, rehearsals, drafts)는 키가 없으면 가짜 응답, 있으면 Claude 호출입니다.
모든 조회와 수정은 기기 ID로 건을 찾습니다(다른 기기의 건은 404).
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.config import is_mock
from app.deps import DeviceId, SessionDep
from app.mock import service
from app.schemas.common import ReportStatus
from app.schemas.reports import (
    DraftOut,
    DraftRequest,
    EvidenceOut,
    GuideOut,
    PhotoUploadOut,
    RehearsalOut,
    RehearsalRequest,
    ReportList,
    ReportOut,
    ReportPatch,
)
from app.services import assist

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportList)
def list_reports(
    device_id: DeviceId,
    session: SessionDep,
    status: ReportStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> ReportList:
    return service.list_reports(session, device_id, status, limit, cursor)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, device_id: DeviceId, session: SessionDep) -> ReportOut:
    return service.report_out(session, service.get_report_record(session, device_id, report_id))


@router.patch("/{report_id}", response_model=ReportOut)
def patch_report(report_id: str, body: ReportPatch, device_id: DeviceId, session: SessionDep) -> ReportOut:
    return service.patch_report(session, service.get_report_record(session, device_id, report_id), body)


@router.get("/{report_id}/evidence", response_model=EvidenceOut)
def get_evidence(report_id: str, device_id: DeviceId, session: SessionDep) -> EvidenceOut:
    return service.evidence_out(session, service.get_report_record(session, device_id, report_id))


@router.post("/{report_id}/photos", status_code=201, response_model=PhotoUploadOut)
def upload_photo(
    report_id: str,
    device_id: DeviceId,
    session: SessionDep,
    photo: Annotated[UploadFile, File()],
    scene_id: Annotated[str | None, Form()] = None,
) -> PhotoUploadOut:
    rec = service.get_report_record(session, device_id, report_id)
    if is_mock():
        service.check_upload(photo)
        return service.upload_photo(session, device_id, rec, scene_id or None)
    return assist.upload_photo(session, device_id, rec, photo, scene_id or None)


@router.post("/{report_id}/rehearsals", response_model=RehearsalOut)
def create_rehearsal(
    report_id: str, device_id: DeviceId, session: SessionDep, body: RehearsalRequest | None = None
) -> RehearsalOut:
    rec = service.get_report_record(session, device_id, report_id)
    photo_id = body.photo_id if body else None
    if is_mock():
        return service.rehearsal(session, device_id, rec, photo_id)
    return assist.rehearsal(session, device_id, rec, photo_id)


@router.get("/{report_id}/guide", response_model=GuideOut)
def get_guide(report_id: str, device_id: DeviceId, session: SessionDep) -> GuideOut:
    return service.guide_out(session, service.get_report_record(session, device_id, report_id))


@router.post("/{report_id}/drafts", response_model=DraftOut)
def create_draft(
    report_id: str, device_id: DeviceId, session: SessionDep, body: DraftRequest | None = None
) -> DraftOut:
    rec = service.get_report_record(session, device_id, report_id)
    tone = body.tone if body else "default"
    if is_mock():
        return service.make_draft(session, rec, tone)
    return assist.make_draft(session, device_id, rec, tone)
