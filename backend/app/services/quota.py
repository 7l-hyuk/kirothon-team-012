"""기기별 하루 AI 호출 상한. 가짜 모드에서는 세지 않습니다.

호출 수는 `ai_usage`에 `(device_id, day)`당 한 행으로 두고(day는 KST 날짜), 상한 검사와 증가를 한 문장의
UPDATE로 처리해 동시에 불러도 상한을 넘지 않습니다.
"""

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import get_settings, is_mock
from app.errors import daily_limit_exceeded
from app.models import AiUsage
from app.timeutil import today_kst


def consume_ai_call(session: Session, device_id: str) -> None:
    """Claude를 부르기 직전에 호출합니다. 상한에 이르렀으면 429, 아니면 호출 수를 1 올리고 바로 커밋합니다.

    실패한 호출도 세어 둡니다(요청이 나갔으면 비용이 들기 때문). 호출 전에는 읽기만 하므로
    이 커밋에 다른 변경이 섞이지 않습니다.
    """
    if is_mock():
        return
    limit = get_settings().ai_daily_limit
    if limit <= 0:
        raise daily_limit_exceeded()
    day = today_kst()

    for _ in range(2):  # 두 번째는 동시 요청이 먼저 행을 만들었을 때
        result = session.execute(
            update(AiUsage)
            .where(AiUsage.device_id == device_id, AiUsage.day == day, AiUsage.count < limit)  # type: ignore[arg-type]
            .values(count=AiUsage.count + 1)
        )
        if result.rowcount == 1:
            session.commit()
            return
        exists = session.exec(
            select(AiUsage.id).where(AiUsage.device_id == device_id, AiUsage.day == day)
        ).first()
        if exists is not None:  # 행은 있는데 갱신이 안 됐으면 상한에 이른 것
            session.rollback()
            raise daily_limit_exceeded()
        try:
            session.add(AiUsage(device_id=device_id, day=day, count=1))
            session.commit()
            return
        except IntegrityError:  # 같은 기기의 동시 요청이 먼저 만들었음. UPDATE부터 다시
            session.rollback()
    raise daily_limit_exceeded()
