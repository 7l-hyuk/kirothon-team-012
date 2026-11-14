"""로컬 디스크 저장소. S3_BUCKET이 없을 때(개발, 테스트)만 씁니다."""

import logging
import os
from pathlib import Path
from uuid import uuid4

from app.errors import not_found, storage_unavailable
from app.storage.base import Storage

logger = logging.getLogger(__name__)


class LocalStorage(Storage):
    kind = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):  # 키가 저장 폴더 밖을 가리키면 거부합니다.
            logger.warning("저장소 오류: 허용되지 않은 키")
            raise storage_unavailable()
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        tmp = path.with_name(f".{uuid4().hex}.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError as exc:
            logger.warning("저장소 오류: %s", type(exc).__name__)
            tmp.unlink(missing_ok=True)
            raise storage_unavailable() from None

    def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            raise not_found() from None
        except OSError as exc:
            logger.warning("저장소 오류: %s", type(exc).__name__)
            raise storage_unavailable() from None

    def url(self, key: str, photo_id: str) -> str:
        return f"/api/photos/{photo_id}/file"
