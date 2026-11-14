"""S3 비공개 버킷 저장소.

- 자격 증명은 코드나 환경변수로 넘기지 않습니다. EC2의 IAM 역할을 boto3가 자동으로 찾습니다.
- ACL을 지정하지 않습니다(버킷은 퍼블릭 접근 차단).
- 조회 주소는 요청마다 만드는 presigned GET URL입니다.
- 오류는 502 storage_unavailable로 바꾸고 로그에는 예외 종류만 남깁니다.
"""

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.errors import storage_unavailable
from app.storage.base import Storage

logger = logging.getLogger(__name__)


def make_client(region: str) -> Any:
    return boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


class S3Storage(Storage):
    kind = "s3"

    def __init__(self, bucket: str, region: str, expires_seconds: int, client: Any | None = None) -> None:
        self.bucket = bucket
        self.expires_seconds = expires_seconds
        self.client = client if client is not None else make_client(region)

    def put(self, key: str, data: bytes) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType="image/jpeg")
        except (ClientError, BotoCoreError) as exc:
            logger.warning("S3 오류(put): %s", type(exc).__name__)
            raise storage_unavailable() from None

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except (ClientError, BotoCoreError) as exc:
            logger.warning("S3 오류(get): %s", type(exc).__name__)
            raise storage_unavailable() from None

    def url(self, key: str, photo_id: str) -> str:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=self.expires_seconds,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("S3 오류(presign): %s", type(exc).__name__)
            raise storage_unavailable() from None
