"""Anthropic SDK 호출은 이 패키지에서만 합니다. 라우터는 SDK를 직접 부르지 않습니다.

- 동기 클라이언트, 시간 초과 50초(CloudFront 오리진 제한 60초보다 짧게), 재시도 없음.
- `temperature`, `top_p`, `top_k`, `thinking`, `budget_tokens`, `tool_choice`, prefill은 보내지 않습니다.
- 응답 본문을 읽기 전에 stop_reason을 확인합니다.
- 로그에는 오류 종류와 상태 코드만 남깁니다. API 키, 사진, 사용자 글은 남기지 않습니다.
"""

import logging
from functools import lru_cache
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.errors import ai_refused, ai_unavailable

logger = logging.getLogger(__name__)

AI_TIMEOUT_SECONDS = 50.0

T = TypeVar("T", bound=BaseModel)


@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=get_settings().anthropic_api_key, timeout=AI_TIMEOUT_SECONDS, max_retries=0
    )


def image_block(b64_jpeg: str) -> dict[str, Any]:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_jpeg}}


def text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def parse_message(
    *, system: str, content: list[dict[str, Any]], output_model: type[T], max_tokens: int
) -> T:
    """Claude를 한 번 부르고 검증된 출력 모델을 돌려줍니다. 실패하면 ApiError(422/502)."""
    try:
        response = get_client().messages.parse(
            model=get_settings().claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=output_model,
        )
    except anthropic.APIConnectionError:  # 시간 초과(APITimeoutError)도 여기에 들어옵니다.
        logger.error("AI 호출 실패: kind=connection")
        raise ai_unavailable() from None
    except anthropic.RateLimitError:
        logger.error("AI 호출 실패: kind=rate_limit status=429")
        raise ai_unavailable() from None
    except anthropic.AuthenticationError:
        logger.error("AI 호출 실패: kind=authentication (API 키를 확인하세요)")
        raise ai_unavailable() from None
    except anthropic.BadRequestError:
        logger.error("AI 호출 실패: kind=bad_request status=400")
        raise ai_unavailable() from None
    except anthropic.APIStatusError as e:
        logger.error("AI 호출 실패: kind=status status=%s", e.status_code)
        raise ai_unavailable() from None
    except ValidationError:
        # 실제 호출에서 재현하지 못한 경로. 방어적으로 502 처리합니다. (tasks.md '미확인 항목' 참고)
        # 정상 경로(parse()와 parsed_output)는 실제 호출로 확인했습니다.
        logger.error("AI 호출 실패: kind=invalid_output")
        raise ai_unavailable() from None

    if response.stop_reason == "refusal":
        logger.warning("AI가 응답을 거절했어요: stop_reason=refusal")
        raise ai_refused()
    parsed = response.parsed_output
    if parsed is None:
        logger.error("AI 호출 실패: kind=empty_output stop_reason=%s", response.stop_reason)
        raise ai_unavailable()
    return parsed
