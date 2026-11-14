"""공통 의존성. X-Device-Id 헤더를 검사합니다. (AI 호출 상한 검사는 다음 Spec)"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.errors import missing_device_id


def get_device_id(x_device_id: Annotated[str | None, Header()] = None) -> str:
    if not x_device_id:
        raise missing_device_id()
    try:
        return str(UUID(x_device_id))
    except ValueError:
        raise missing_device_id() from None


DeviceId = Annotated[str, Depends(get_device_id)]
