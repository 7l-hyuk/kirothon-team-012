"""사진 파일 조회. 로컬 디스크 저장소(S3_BUCKET 없음)일 때만 파일을 돌려줍니다.

<img> 태그는 헤더를 보내지 못해 X-Device-Id를 검사하지 않습니다. 추측할 수 없는 UUID가 접근 열쇠입니다.
S3 저장소에서는 응답의 사진 url이 presigned URL이라 이 경로를 쓰지 않으며 404입니다.
"""

from fastapi import APIRouter, Response

from app.deps import SessionDep
from app.errors import not_found
from app.services import store
from app.storage import get_storage, storage_kind

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/{photo_id}/file", include_in_schema=False)
def get_photo_file(photo_id: str, session: SessionDep) -> Response:
    if storage_kind() != "local":
        raise not_found()
    photo = store.get_photo(session, photo_id)
    if photo is None or photo.s3_key is None:  # 없는 ID, 또는 파일 없는 가짜 모드 자리표시
        raise not_found()
    return Response(
        get_storage().get(photo.s3_key),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )
