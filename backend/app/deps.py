"""공통 의존성. X-Device-Id 헤더 검사, 요청 단위 DB 세션."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlmodel import Session

from app import db
from app.errors import missing_device_id


def get_device_id(x_device_id: Annotated[str | None, Header()] = None) -> str:
    if not x_device_id:
        raise missing_device_id()
    try:
        return str(UUID(x_device_id))
    except ValueError:
        raise missing_device_id() from None


DeviceId = Annotated[str, Depends(get_device_id)]


def get_session() -> Iterator[Session]:
    """요청마다 세션을 열고 닫습니다. DB가 준비되지 않았으면 503. 커밋은 쓰는 서비스가 직접 합니다."""
    db.ensure_ready()
    with Session(db.get_engine(), expire_on_commit=False) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
