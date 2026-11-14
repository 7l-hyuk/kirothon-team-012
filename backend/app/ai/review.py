"""증거 사진 검수 호출."""

import base64

from app.ai import prompts
from app.ai.client import image_block, parse_message, text_block
from app.schemas.ai_outputs import ReviewOutput


def run(jpeg: bytes, scene_label: str, pass_criteria: str) -> ReviewOutput:
    content = [
        image_block(base64.standard_b64encode(jpeg).decode("ascii")),
        text_block(prompts.review_user_text(scene_label, pass_criteria)),
    ]
    return parse_message(
        system=prompts.review_system(), content=content, output_model=ReviewOutput, max_tokens=1000
    )
