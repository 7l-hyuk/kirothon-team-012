"""불법주정차 사전 점검 호출."""

import base64

from app.ai import prompts
from app.ai.client import image_block, parse_message, text_block
from app.schemas.ai_outputs import RehearsalOutput
from app.services.procedures import Procedure


def run(jpeg: bytes, proc: Procedure) -> RehearsalOutput:
    content = [
        image_block(base64.standard_b64encode(jpeg).decode("ascii")),
        text_block(prompts.rehearsal_user_text()),
    ]
    return parse_message(
        system=prompts.rehearsal_system(proc),
        content=content,
        output_model=RehearsalOutput,
        max_tokens=1500,
    )
