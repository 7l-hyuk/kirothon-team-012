"""가짜 사진 자리표시. <img> 태그는 헤더를 못 보내므로 X-Device-Id 검사를 하지 않습니다."""

from fastapi import APIRouter, Response

from app.mock.fixtures import PLACEHOLDER_SVG

router = APIRouter(prefix="/api/mock", tags=["mock"])


@router.get("/placeholder.svg", include_in_schema=False)
async def placeholder() -> Response:
    return Response(
        PLACEHOLDER_SVG,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
