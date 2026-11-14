"""사진 저장소 인터페이스. 라우터와 서비스는 구현이 아니라 이 인터페이스만 씁니다."""

from abc import ABC, abstractmethod


class Storage(ABC):
    kind: str  # "s3" 또는 "local"

    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
        """사진 바이트를 키로 저장합니다. 실패하면 502 storage_unavailable."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """저장된 바이트를 읽습니다. 실패하면 502 storage_unavailable(로컬은 파일이 없으면 404)."""

    @abstractmethod
    def url(self, key: str, photo_id: str) -> str:
        """API 응답에 넣을 사진 주소. 저장하지 않고 요청 때마다 만듭니다."""
