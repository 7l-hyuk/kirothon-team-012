import uuid

from fastapi.testclient import TestClient

from app import db
from app.main import create_app


def test_health_without_db(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "unavailable", "mock": True}
    assert r.headers["X-Mock"] == "true"


def test_health_with_db(client, monkeypatch):
    monkeypatch.setattr(db, "check_db", lambda: True)
    assert client.get("/api/health").json()["db"] == "ok"


def test_root_without_static(client):
    assert client.get("/").json() == {"service": "shingomate", "docs": "/docs"}


def test_missing_device_id_is_400(client):
    r = client.get("/api/reports")
    assert r.status_code == 400
    assert r.json()["code"] == "missing_device_id"
    assert r.json()["detail"]


def test_invalid_device_id_is_400(client):
    r = client.get("/api/reports", headers={"X-Device-Id": "not-a-uuid"})
    assert r.status_code == 400
    assert r.json()["code"] == "missing_device_id"


def test_placeholder_needs_no_device_id(client):
    r = client.get("/api/mock/placeholder.svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")


def test_spa_serving(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "logo.txt").write_text("logo")
    c = TestClient(create_app(static_dir=tmp_path))
    assert "app" in c.get("/").text
    assert "app" in c.get("/reports/123").text  # 클라이언트 라우트는 index.html
    assert c.get("/logo.txt").text == "logo"
    assert "root:" not in c.get("/..%2f..%2f..%2fetc/passwd").text  # 경로 탈출 방지
    r = c.get("/api/nope", headers={"X-Device-Id": str(uuid.uuid4())})
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert c.get("/api/health").json()["status"] == "ok"
