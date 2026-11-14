"""사진 저장소. 인터페이스 하나(Storage)와 구현 둘(S3Storage, LocalStorage).

S3_BUCKET이 있으면 S3, 없으면 UPLOAD_DIR 디스크입니다. 라우터와 서비스는 get_storage()로만 받습니다.
"""

from app.config import get_settings
from app.storage.base import Storage
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage

__all__ = ["Storage", "S3Storage", "LocalStorage", "get_storage", "storage_kind"]

_cache: tuple[tuple, Storage] | None = None


def storage_kind() -> str:
    """설정만 보고 "s3" 또는 "local"을 돌려줍니다. S3 클라이언트를 만들지 않습니다."""
    return "s3" if get_settings().s3_bucket else "local"


def get_storage() -> Storage:
    """설정이 같으면 같은 객체를 돌려줍니다(S3 클라이언트를 매번 만들지 않기 위해서)."""
    global _cache
    s = get_settings()
    cache_key = (s.s3_bucket, s.aws_region, s.presign_expires_seconds, s.upload_dir)
    if _cache is None or _cache[0] != cache_key:
        storage: Storage
        if s.s3_bucket:
            storage = S3Storage(s.s3_bucket, s.aws_region, s.presign_expires_seconds)
        else:
            storage = LocalStorage(s.upload_dir)
        _cache = (cache_key, storage)
    return _cache[1]
