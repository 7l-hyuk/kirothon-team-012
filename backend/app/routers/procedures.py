"""신고 절차 데이터 조회. backend/data/{type_id}.json 내용을 그대로 돌려줍니다."""

from typing import Any

from fastapi import APIRouter

from app.deps import DeviceId
from app.errors import not_found
from app.services import procedures

router = APIRouter(prefix="/api/procedures", tags=["procedures"])


@router.get("/{type_id}")
def get_procedure(type_id: str, device_id: DeviceId) -> dict[str, Any]:
    raw = procedures.raw_procedure(type_id)
    if raw is None:
        raise not_found()
    return raw
