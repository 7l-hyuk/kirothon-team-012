"""신고 문구 대필 호출. 사진은 보내지 않고 분석 요약과 위치, 일시만 보냅니다."""

from app.ai import prompts
from app.ai.client import parse_message, text_block
from app.schemas.ai_outputs import DraftOutput
from app.services.procedures import Procedure


def run(
    procs: dict[str, Procedure],
    *,
    type_id: str,
    zone_label: str | None,
    summary: str,
    reason: str | None,
    location: str,
    when: str,
    tone: str,
) -> DraftOutput:
    proc = procs[type_id]
    user = prompts.draft_user_text(
        type_id=type_id,
        label=proc.label,
        zone_label=zone_label,
        summary=summary,
        reason=reason,
        location=location,
        when=when,
        tone=tone,
    )
    return parse_message(
        system=prompts.draft_system({type_id: proc}),
        content=[text_block(user)],
        output_model=DraftOutput,
        max_tokens=1000,
    )
