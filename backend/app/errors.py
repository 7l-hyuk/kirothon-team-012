"""오류 코드, 공통 예외, 처리기. 응답 형태는 항상 {"detail": "해요체", "code": "snake_case"}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode:
    MISSING_DEVICE_ID = "missing_device_id"
    NOT_FOUND = "not_found"
    INVALID_STATE = "invalid_state"
    PHOTO_TOO_LARGE = "photo_too_large"
    UNSUPPORTED_MEDIA = "unsupported_media"
    VALIDATION_ERROR = "validation_error"
    AI_REFUSED = "ai_refused"
    DAILY_LIMIT_EXCEEDED = "daily_limit_exceeded"
    AI_UNAVAILABLE = "ai_unavailable"
    # 명세 밖의 보조 코드
    METHOD_NOT_ALLOWED = "method_not_allowed"
    INTERNAL_ERROR = "internal_error"


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def missing_device_id() -> ApiError:
    return ApiError(400, ErrorCode.MISSING_DEVICE_ID, "기기 정보를 확인할 수 없어요. 앱을 새로고침해 주세요.")


def not_found() -> ApiError:
    return ApiError(404, ErrorCode.NOT_FOUND, "찾을 수 없어요. 목록에서 다시 골라 주세요.")


def invalid_state(detail: str) -> ApiError:
    return ApiError(409, ErrorCode.INVALID_STATE, detail)


def validation_error(detail: str) -> ApiError:
    return ApiError(422, ErrorCode.VALIDATION_ERROR, detail)


def unsupported_media() -> ApiError:
    return ApiError(415, ErrorCode.UNSUPPORTED_MEDIA, "JPEG, PNG, WebP 사진만 올릴 수 있어요.")


def photo_too_large() -> ApiError:
    return ApiError(413, ErrorCode.PHOTO_TOO_LARGE, "사진이 너무 커요. 10MB 이하로 올려 주세요.")


def ai_refused() -> ApiError:
    return ApiError(422, ErrorCode.AI_REFUSED, "AI가 이번 요청에는 답하지 못했어요. 다시 시도해 주세요.")


def ai_unavailable() -> ApiError:
    return ApiError(502, ErrorCode.AI_UNAVAILABLE, "AI가 지금 답하지 못했어요. 잠시 뒤 다시 시도해 주세요.")


def daily_limit_exceeded() -> ApiError:
    return ApiError(
        429, ErrorCode.DAILY_LIMIT_EXCEEDED, "오늘 쓸 수 있는 AI 분석 횟수를 모두 썼어요. 내일 다시 이용해 주세요."
    )


def _body(detail: str, code: str) -> dict[str, str]:
    return {"detail": detail, "code": code}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(exc.detail, exc.code), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # 필드 이름만 알려 줍니다. 입력값 원문은 응답에 넣지 않습니다.
        field = ""
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path", "header")]
            if loc:
                field = loc[-1]
                break
        detail = f"'{field}' 값을 확인해 주세요." if field else "입력한 내용을 확인해 주세요."
        return JSONResponse(_body(detail, ErrorCode.VALIDATION_ERROR), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            body = _body("찾을 수 없어요. 주소를 다시 확인해 주세요.", ErrorCode.NOT_FOUND)
        elif exc.status_code == 405:
            body = _body("지원하지 않는 요청이에요.", ErrorCode.METHOD_NOT_ALLOWED)
        else:
            body = _body("요청을 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.", ErrorCode.INTERNAL_ERROR)
        return JSONResponse(body, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            _body("잠시 문제가 생겼어요. 다시 시도해 주세요.", ErrorCode.INTERNAL_ERROR),
            status_code=500,
        )
