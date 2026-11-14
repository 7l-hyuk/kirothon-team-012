"""DB 엔진과 시작 처리.

- 엔진은 처음 쓸 때 만듭니다. 연결에 실패해도 앱은 뜹니다.
- 시작할 때 `init_db()`가 테이블을 만들고, DB가 아직 준비되지 않았으면 2초 간격으로 최대 15번 다시 시도합니다.
- 끝내 실패하면 DB가 필요한 요청은 `ensure_ready()`에서 503(db_unavailable)이 됩니다. DB가 나중에 살아나면 재시작 없이 복구됩니다.
- 마이그레이션 도구는 쓰지 않습니다(`create_all`만).
"""

import logging
import threading
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from app import models  # noqa: F401  (테이블을 metadata에 등록)
from app.config import get_settings
from app.errors import db_unavailable

logger = logging.getLogger(__name__)

RETRY_ATTEMPTS = 15
RETRY_DELAY_SECONDS = 2.0
RECHECK_INTERVAL_SECONDS = 2.0

_engine: Engine | None = None
_ready = False
_last_attempt = float("-inf")
_lock = threading.Lock()


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 2}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engine


def create_tables() -> None:
    SQLModel.metadata.create_all(get_engine())


def init_db(attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY_SECONDS) -> bool:
    """테이블을 만듭니다. 실패하면 `delay`초 간격으로 `attempts`번까지 시도하고, 끝내 안 되면 False.

    비밀번호가 로그에 남지 않게 예외 종류만 기록합니다.
    """
    global _ready
    for attempt in range(1, attempts + 1):
        try:
            create_tables()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DB 준비 실패 (%d/%d): %s", attempt, attempts, type(exc).__name__)
            if attempt < attempts:
                time.sleep(delay)
        else:
            _ready = True
            logger.info("DB 준비 완료")
            return True
    logger.error("DB를 준비하지 못했어요. DB가 필요한 요청은 503으로 응답합니다.")
    return False


def ensure_ready() -> None:
    """DB가 필요한 요청이 부릅니다. 준비되지 않았으면 한 번 다시 시도하고, 안 되면 503."""
    global _ready, _last_attempt
    if _ready:
        return
    with _lock:
        if _ready:
            return
        now = time.monotonic()
        if now - _last_attempt < RECHECK_INTERVAL_SECONDS:  # 요청마다 연결을 기다리지 않게 간격을 둡니다.
            raise db_unavailable()
        _last_attempt = now
        try:
            create_tables()
        except Exception as exc:  # noqa: BLE001
            logger.warning("DB 연결 확인 실패: %s", type(exc).__name__)
            raise db_unavailable() from None
        _ready = True


def check_db() -> bool:
    """DB에 연결해 SELECT 1이 되면 True. 어떤 오류든 False (비밀번호가 로그에 남지 않게 예외 종류만 기록)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB 연결 확인 실패: %s", type(exc).__name__)
        return False
