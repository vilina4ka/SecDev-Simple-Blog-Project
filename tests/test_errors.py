"""Тесты для обработки ошибок в формате RFC 7807."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_not_found_item():
    """Проверка формата ошибки 404 в RFC 7807."""
    r = client.get("/items/999")
    assert r.status_code == 404
    body = r.json()
    assert "type" in body
    assert "title" in body
    assert "status" in body
    assert body["status"] == 404
    assert "correlation_id" in body
    assert "X-Correlation-ID" in r.headers


def test_validation_error():
    """Проверка формата ошибки валидации в RFC 7807."""
    r = client.post("/items", json={"name": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["type"] == "https://example.com/problems/validation-error"
    assert body["title"] == "Validation Error"
    assert body["status"] == 422
    assert "correlation_id" in body
