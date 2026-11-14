"""신고 건 API (S1, S4~S11). 검증과 응답 변환만 하고 로직은 app.mock.service에 둡니다."""

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.deps import DeviceId
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

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportList)
async def list_reports(
    device_id: DeviceId,
    status: ReportStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> ReportList:
    return service.list_reports(device_id, status, limit, cursor)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: str, device_id: DeviceId) -> ReportOut:
    return service.report_out(service.get_report_record(device_id, report_id))


@router.patch("/{report_id}", response_model=ReportOut)
async def patch_report(report_id: str, body: ReportPatch, device_id: DeviceId) -> ReportOut:
    return service.patch_report(service.get_report_record(device_id, report_id), body)


@router.get("/{report_id}/evidence", response_model=EvidenceOut)
async def get_evidence(report_id: str, device_id: DeviceId) -> EvidenceOut:
    return service.evidence_out(service.get_report_record(device_id, report_id))


@router.post("/{report_id}/photos", status_code=201, response_model=PhotoUploadOut)
async def upload_photo(
    report_id: str,
    device_id: DeviceId,
    photo: Annotated[UploadFile, File()],
    scene_id: Annotated[str | None, Form()] = None,
) -> PhotoUploadOut:
    rec = service.get_report_record(device_id, report_id)
    await service.check_upload(photo)
    return service.upload_photo(rec, scene_id or None)


@router.post("/{report_id}/rehearsals", response_model=RehearsalOut)
async def create_rehearsal(
    report_id: str, device_id: DeviceId, body: RehearsalRequest | None = None
) -> RehearsalOut:
    rec = service.get_report_record(device_id, report_id)
    return service.rehearsal(device_id, rec, body.photo_id if body else None)


@router.get("/{report_id}/guide", response_model=GuideOut)
async def get_guide(report_id: str, device_id: DeviceId) -> GuideOut:
    return service.guide_out(service.get_report_record(device_id, report_id))


@router.post("/{report_id}/drafts", response_model=DraftOut)
async def create_draft(
    report_id: str, device_id: DeviceId, body: DraftRequest | None = None
) -> DraftOut:
    rec = service.get_report_record(device_id, report_id)
    return service.make_draft(rec, body.tone if body else "default")
