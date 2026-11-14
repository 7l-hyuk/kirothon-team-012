"""사례 공유 글 작성 호출. 사진은 보내지 않고, 상세 주소·접수번호·일이 빠진 자료(CaseFacts)만 보냅니다."""

from app.ai import prompts
from app.ai.client import parse_message, text_block
from app.schemas.ai_outputs import CaseDraftOutput
from app.schemas.cases import CaseFacts
from app.services.procedures import Procedure


def run(facts: CaseFacts, proc: Procedure) -> CaseDraftOutput:
    return parse_message(
        system=prompts.case_system(proc),
        content=[text_block(prompts.case_user_text(facts))],
        output_model=CaseDraftOutput,
        max_tokens=1500,
    )
