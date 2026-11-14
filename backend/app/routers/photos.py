"""임시 사진 파일 조회. <img> 태그는 헤더를 보내지 못해 X-Device-Id를 검사하지 않습니다.

추측할 수 없는 UUID가 접근 열쇠입니다. 다음 Spec에서 S3 presigned URL로 바꿉니다.
"""

from fastapi import APIRouter, Response

from app.errors import not_found
from app.services.store import store

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/{photo_id}/file", include_in_schema=False)
def get_photo_file(photo_id: str) -> Response:
    record = store.photos.get(photo_id)
    if record is None:
        raise not_found()
    return Response(
        record.data,
        media_type=record.media_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
