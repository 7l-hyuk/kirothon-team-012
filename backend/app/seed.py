"""예시 사례(seed). 앱이 시작될 때 `cases`가 비어 있으면 backend/data/seed_cases.json의 3건을 넣습니다.

예시 사례는 `is_seed`로 표시하고 어느 기기의 것도 아닙니다(device_id, report_id가 NULL). 사진은 없습니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import db
from app.models import Case
from app.schemas.common import TypeId
from app.services.cases import HEADINGS

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "seed_cases.json"


class SeedSection(BaseModel):
    heading: str
    body: str


class SeedCase(BaseModel):
    key: str
    type_id: TypeId
    title: str
    result_label: str
    district: str
    period: str
    like_count: int
    created_at: datetime
    sections: list[SeedSection]


def load_seed_cases(path: Path = SEED_PATH) -> list[SeedCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = [SeedCase.model_validate(c) for c in raw["cases"]]
    for c in cases:
        if tuple(s.heading for s in c.sections) != HEADINGS:
            raise ValueError(f"예시 사례 '{c.key}'의 절 제목이 5개 절과 달라요")
    return cases


def seed_cases(session: Session) -> int:
    """`cases`가 비어 있으면 예시를 넣고 넣은 개수를 돌려줍니다. 이미 있으면 0입니다."""
    if session.exec(select(Case.id).limit(1)).first() is not None:
        return 0
    rows = [
        Case(
            id=str(uuid5(NAMESPACE_URL, f"shingomate:{c.key}")),
            report_id=None,
            device_id=None,
            type_id=c.type_id,
            title=c.title,
            sections=[s.model_dump() for s in c.sections],
            result_label=c.result_label,
            district=c.district,
            period=c.period,
            like_count=c.like_count,
            is_seed=True,
            created_at=c.created_at,
        )
        for c in load_seed_cases()
    ]
    session.add_all(rows)
    try:
        session.commit()
    except IntegrityError:  # 다른 프로세스가 먼저 넣었어요.
        session.rollback()
        return 0
    return len(rows)


def seed_on_startup() -> None:
    """lifespan에서 부릅니다. 실패해도 앱은 뜹니다(오류 종류만 기록)."""
    try:
        with Session(db.get_engine()) as session:
            count = seed_cases(session)
        if count:
            logger.info("예시 사례 %d건을 넣었어요", count)
    except Exception as exc:  # noqa: BLE001
        logger.warning("예시 사례를 넣지 못했어요: %s", type(exc).__name__)
