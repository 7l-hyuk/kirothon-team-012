"""시각 컬럼 타입. 쓸 때는 UTC로 바꿔 저장하고, 읽을 때는 항상 KST 값으로 돌려줍니다.

PostgreSQL은 timestamptz로 저장합니다. SQLite(테스트)는 timezone을 저장하지 못하므로 UTC로 간주합니다.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from app.timeutil import KST


class KSTDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(KST)
