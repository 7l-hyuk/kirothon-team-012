"""업로드 사진 검사와 축소. 저장은 app.services.store.new_photo와 app.storage가 합니다.

AI에는 긴 변 1568px 이하 JPEG만 보냅니다(용량과 응답 시간 때문). 저장하는 파일도 같은 JPEG입니다.
"""

import io

from fastapi import UploadFile

from app.errors import photo_too_large, unsupported_media

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_EDGE = 1568
JPEG_QUALITY = 85


def read_upload(file: UploadFile) -> bytes:
    """MIME 형식과 용량을 검사하고 원본 바이트를 돌려줍니다. (415, 413)"""
    if file.content_type not in ALLOWED_MIME:
        raise unsupported_media()
    data = file.file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise photo_too_large()
    return data


def shrink_to_jpeg(raw: bytes) -> bytes:
    """긴 변 1568px 이하 JPEG로 줄입니다. 이미지로 열 수 없으면 415."""
    from PIL import Image, ImageOps  # 가짜 모드는 Pillow 없이도 뜨도록 여기서 불러옵니다.

    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ALLOWED_FORMATS:
                raise unsupported_media()
            img = ImageOps.exif_transpose(img).convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))  # 투명 배경은 흰색으로
            flat.paste(img, mask=img.getchannel("A"))
            flat.thumbnail((MAX_EDGE, MAX_EDGE))
            out = io.BytesIO()
            flat.save(out, format="JPEG", quality=JPEG_QUALITY)
            return out.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):  # UnidentifiedImageError는 OSError
        raise unsupported_media() from None


def prepare_upload(file: UploadFile) -> bytes:
    return shrink_to_jpeg(read_upload(file))
