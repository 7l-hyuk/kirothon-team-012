import uuid

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.mock.store import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


@pytest.fixture(autouse=True)
def _no_real_db(monkeypatch):
    # 테스트는 실제 DB에 붙지 않습니다.
    monkeypatch.setattr(db, "check_db", lambda: False)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-Device-Id": str(uuid.uuid4())}


JPEG = ("a.jpg", b"fake-image", "image/jpeg")
