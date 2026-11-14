import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import db
from app.ai import client as ai_client
from app.config import get_settings
from app.main import app
from app.services.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


@pytest.fixture(autouse=True)
def _no_real_db(monkeypatch):
    # 테스트는 실제 DB에 붙지 않습니다.
    monkeypatch.setattr(db, "check_db", lambda: False)


@pytest.fixture(autouse=True)
def _mock_mode_by_default(monkeypatch, tmp_path):
    """기본은 키 없는 가짜 모드입니다. 개발자의 환경변수와 backend/.env 가 섞이지 않게 합니다."""
    monkeypatch.chdir(tmp_path)  # .env 는 현재 디렉터리 기준으로 읽습니다.
    for name in ("ANTHROPIC_API_KEY", "CLAUDE_MODEL", "AI_DAILY_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-Device-Id": str(uuid.uuid4())}


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
