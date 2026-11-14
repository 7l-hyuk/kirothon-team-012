"""기기별 하루 AI 호출 상한. 가짜 모드에서는 세지 않습니다."""

from datetime import datetime, timedelta, timezone

from app.config import get_settings, is_mock
from app.errors import daily_limit_exceeded
from app.services.store import store

KST = timezone(timedelta(hours=9))


def consume_ai_call(device_id: str) -> None:
    """Claude를 부르기 직전에 호출합니다. 상한에 이르렀으면 429, 아니면 호출 수를 1 올립니다.

    실패한 호출도 세어 둡니다(요청이 나갔으면 비용이 들기 때문).
    """
    if is_mock():
        return
    limit = get_settings().ai_daily_limit
    today = datetime.now(KST).date().isoformat()
    with store.lock:
        for key in [k for k in store.ai_usage if k[1] != today]:  # 지난 날짜는 버립니다.
            del store.ai_usage[key]
        used = store.ai_usage.get((device_id, today), 0)
        if used >= limit:
            raise daily_limit_exceeded()
        store.ai_usage[(device_id, today)] = used + 1
