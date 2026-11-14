import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import db
from app import storage as storage_module
from app.ai import client as ai_client
from app.config import get_settings
from app.main import app
from app.models import Photo
from app.storage import get_storage


def make_sqlite_engine(url: str = "sqlite://"):
    """테스트용 SQLite 엔진. 메모리 DB는 StaticPool로 연결 하나를 모든 스레드가 같이 씁니다."""
    if url == "sqlite://":
        return create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_engine(url, connect_args={"check_same_thread": False})


@pytest.fixture(autouse=True)
def _sqlite_db():
    """요청이 쓰는 DB를 SQLite 메모리 DB로 바꿉니다. PostgreSQL에는 붙지 않습니다."""
    engine = make_sqlite_engine()
    SQLModel.metadata.create_all(engine)
    db._engine = engine
    db._ready = True
    db._last_attempt = float("-inf")
    yield engine
    engine.dispose()
    db._engine = None
    db._ready = False
    db._last_attempt = float("-inf")


@pytest.fixture(autouse=True)
def _no_real_db(monkeypatch):
    # /api/health 의 db 상태는 기본으로 "연결 안 됨"으로 둡니다(요청이 쓰는 DB는 위의 SQLite입니다).
    monkeypatch.setattr(db, "check_db", lambda: False)


@pytest.fixture(autouse=True)
def _mock_mode_by_default(monkeypatch, tmp_path):
    """기본은 키 없는 가짜 모드입니다. 개발자의 환경변수와 backend/.env 가 섞이지 않게 합니다.

    사진은 임시 폴더의 LocalStorage에 저장합니다(S3_BUCKET 없음).
    """
    monkeypatch.chdir(tmp_path)  # .env 는 현재 디렉터리 기준으로 읽습니다.
    for name in (
        "ANTHROPIC_API_KEY",
        "CLAUDE_MODEL",
        "AI_DAILY_LIMIT",
        "S3_BUCKET",
        "AWS_REGION",
        "PRESIGN_EXPIRES_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    storage_module._cache = None
    yield
    get_settings.cache_clear()
    storage_module._cache = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-Device-Id": str(uuid.uuid4())}


# ---- DB와 저장소를 직접 들여다보는 도우미 (옛 메모리 저장소 접근을 대신합니다) ----
def count_rows(model) -> int:
    """테이블의 행 수."""
    with Session(db.get_engine()) as session:
        return session.exec(select(func.count()).select_from(model)).one()


def set_photo_bytes(photo_id: str, data: bytes) -> None:
    """저장된 사진 파일의 내용을 바꿉니다(어느 사진이 AI에 갔는지 구분하기 위해서)."""
    with Session(db.get_engine()) as session:
        key = session.get(Photo, photo_id).s3_key
    get_storage().put(key, data)


# 가짜 모드 테스트용: 이미지로 열 수 없는 바이트입니다.
JPEG = ("a.jpg", b"fake-image", "image/jpeg")


def make_image(fmt: str = "JPEG", size: tuple[int, int] = (200, 100), mode: str = "RGB") -> bytes:
    """실제로 열리는 이미지 바이트. 실제 모드 테스트에서 씁니다."""
    from PIL import Image

    buf = io.BytesIO()
    color = (120, 130, 140, 128) if mode == "RGBA" else (120, 130, 140)
    Image.new(mode, size, color).save(buf, format=fmt)
    return buf.getvalue()


class FakeMessages:
    def __init__(self) -> None:
        self.queue: list = []
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeClient:
    """anthropic.Anthropic 대신 끼워 넣는 가짜. messages.parse()가 parsed_output, stop_reason을 가진 객체를 돌려줍니다."""

    def __init__(self) -> None:
        self.messages = FakeMessages()

    def reply(self, parsed, stop_reason: str = "end_turn") -> None:
        self.messages.queue.append(SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed))

    def fail(self, exc: BaseException) -> None:
        self.messages.queue.append(exc)

    @property
    def calls(self) -> list[dict]:
        return self.messages.calls


@pytest.fixture
def ai(monkeypatch) -> FakeClient:
    """키가 있는 실제 모드. Anthropic 클라이언트를 가짜로 바꿔 끼웁니다(실제 호출 없음)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("AI_DAILY_LIMIT", "20")
    get_settings.cache_clear()
    fake = FakeClient()
    monkeypatch.setattr(ai_client, "get_client", lambda: fake)
    return fake
