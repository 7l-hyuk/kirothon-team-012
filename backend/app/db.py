"""DB 엔진. 처음 쓸 때 만들고, 연결에 실패해도 앱은 뜹니다.
테이블 생성과 seed는 다음 Spec에서 합니다."""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            connect_args={"connect_timeout": 2},
            pool_pre_ping=True,
        )
    return _engine


def check_db() -> bool:
    """DB에 연결해 SELECT 1이 되면 True. 어떤 오류든 False (비밀번호가 로그에 남지 않게 예외 종류만 기록)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB 연결 확인 실패: %s", type(exc).__name__)
        return False
