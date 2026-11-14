"""시각 도우미. 응답은 KST(+09:00), DB에는 UTC로 저장합니다(app.models.types.KSTDateTime)."""

from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST).replace(microsecond=0)


def today_kst() -> date:
    return datetime.now(KST).date()
