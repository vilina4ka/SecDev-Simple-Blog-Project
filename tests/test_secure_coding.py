import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Проверка эндпоинта /health."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.skip("P05: placeholder test for RFC7807 validation error")
def test_rfc7807_validation_error():
    pass


@pytest.mark.skip("P05: placeholder test for long title returns 422")
def test_long_title_returns_422():
    pass


@pytest.mark.skip("P05: placeholder test for editing others post returns 403")
def test_403_on_editing_others_post():
    pass


@pytest.mark.skip("P05: placeholder test for expired JWT handling")
def test_expired_jwt():
    pass


@pytest.mark.skip("P05: placeholder test for /login rate limiting")
def test_login_rate_limit():
    pass
