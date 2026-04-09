"""Smoke-тесты API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    """GET /health возвращает ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root() -> None:
    """Корень отвечает."""
    r = client.get("/")
    assert r.status_code == 200
    assert "service" in r.json()
