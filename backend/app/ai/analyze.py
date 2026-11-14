"""상황 분석 호출."""

import base64

from app.ai import prompts
from app.ai.client import image_block, parse_message, text_block
from app.schemas.ai_outputs import AnalysisOutput
from app.services.procedures import Procedure


def run(
    jpegs: list[bytes], text: str | None, address: str | None, procs: dict[str, Procedure]
) -> AnalysisOutput:
    content: list[dict] = []
    for i, data in enumerate(jpegs, start=1):
        content.append(text_block(f"사진 {i}"))
        content.append(image_block(base64.standard_b64encode(data).decode("ascii")))
    content.append(text_block(prompts.analysis_user_text(text, address, len(jpegs))))
    return parse_message(
        system=prompts.analysis_system(procs),
        content=content,
        output_model=AnalysisOutput,
        max_tokens=4000,
    )
