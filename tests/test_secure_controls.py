from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.auth import create_access_token, get_current_user, verify_token
from app.main import app
from app.src.schemas import validate_tag

client = TestClient(app)


def test_rate_limit_ip_exceeded():
    """Негативный тест: превышение rate limit по IP (ADR-002, NFR-01, R1)."""
    from app.src.rate_limit import _rate_limit_store

    _rate_limit_store.clear()

    for i in range(6):
        resp = client.post("/login", json={"username": f"user{i}", "password": "wrongpwd"})
        if i < 5:
            assert resp.status_code == 401, f"Request {i} should be 401, got {resp.status_code}"
        else:
            assert resp.status_code == 429, f"Request {i} should be 429, got {resp.status_code}"
            assert "Retry-After" in resp.headers
            body = resp.json()
            assert "Too many requests" in body.get("detail", "")


def test_rate_limit_account_exceeded():
    """Негативный тест: превышение rate limit по аккаунту (ADR-002, NFR-01, R1)."""
    from app.src.rate_limit import _rate_limit_store

    _rate_limit_store.clear()

    username = "testuser_account_limit"
    ip_limit_hit = False
    account_limit_hit = False

    for i in range(21):
        resp = client.post("/login", json={"username": username, "password": "wrongpwd"})

        if resp.status_code == 429:
            assert "Retry-After" in resp.headers
            body = resp.json()
            detail = body.get("detail", "")
            if "Too many requests" in detail and not ip_limit_hit:
                ip_limit_hit = True
                assert i >= 4, f"IP rate limit should trigger after 5 requests, got at {i}"
            elif "Too many login attempts" in detail:

                account_limit_hit = True
                assert i >= 19, f"Account rate limit should trigger after 20 requests, got at {i}"
        elif i < 5:
            assert resp.status_code in [
                401,
                429,
            ], f"Request {i} should be 401 or 429, got {resp.status_code}"
        else:
            assert resp.status_code in [
                401,
                429,
            ], f"Request {i} should be 401 or 429, got {resp.status_code}"

    assert ip_limit_hit or account_limit_hit, "At least one rate limit should have been triggered"


def test_integer_overflow_id_negative():
    """Негативный тест: отрицательный ID (защита от integer overflow)."""
    resp = client.get("/posts/-1")
    assert resp.status_code == 400
    body = resp.json()
    assert body["title"] == "Invalid Id"
    assert "positive" in body["detail"].lower()


def test_integer_overflow_id_too_large():
    """Негативный тест: ID превышает максимальное значение (защита от integer overflow)."""
    large_id = 2147483648
    resp = client.get(f"/posts/{large_id}")
    assert resp.status_code == 400
    body = resp.json()
    assert body["title"] == "Id Overflow"
    assert "exceeds maximum" in body["detail"].lower()


def test_sql_injection_in_tag():
    """Негативный тест: SQL injection паттерн в теге (защита от SQL injection)."""
    malicious_tags = ["'; DROP TABLE posts; --", "union select", "exec xp_cmdshell"]

    for tag in malicious_tags:
        with pytest.raises(ValueError, match="invalid"):
            validate_tag(tag)


def test_sql_injection_in_tag_filter():
    """Негативный тест: SQL injection в фильтре по тегу через GET параметр."""
    resp = client.get("/posts?tag='; DROP TABLE posts; --")
    assert resp.status_code == 400
    body = resp.json()
    assert body["title"] == "Invalid Tag"
    assert "invalid" in body["detail"].lower()


def test_tag_with_special_characters():
    """Негативный тест: тег с недопустимыми символами."""
    invalid_tags = ["tag with spaces", "tag@domain", "tag#hash", "tag$money"]

    for tag in invalid_tags:
        with pytest.raises(ValueError):
            validate_tag(tag)


def test_tag_too_long():
    """Негативный тест: тег превышает максимальную длину (50 символов)."""
    long_tag = "a" * 51
    with pytest.raises(ValueError, match="at most 50"):
        validate_tag(long_tag)


def test_too_many_tags():
    """Негативный тест: слишком много тегов (максимум 10)."""
    too_many_tags = [f"tag{i}" for i in range(11)]
    resp = client.post(
        "/posts",
        json={
            "title": "Test",
            "body": "Test body",
            "status": "draft",
            "tags": too_many_tags,
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    detail_str = str(body["detail"]).lower()
    assert "maximum" in detail_str or "at most" in detail_str or "10" in detail_str


def test_owner_only_update_unauthorized():
    resp = client.post(
        "/posts",
        json={
            "title": "My Post",
            "body": "Content",
            "status": "draft",
            "tags": [],
        },
        headers={"X-User-Id": "user1"},
    )
    assert resp.status_code == 200
    post_id = resp.json()["id"]

    resp = client.patch(
        f"/posts/{post_id}",
        json={"title": "Hacked"},
        headers={"X-User-Id": "user2"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["title"] == "Forbidden"
    assert "own posts" in body["detail"].lower()


def test_owner_only_delete_unauthorized():
    """Негативный тест: попытка удалить чужой пост (NFR-02, NFR-03, R3)."""
    resp = client.post(
        "/posts",
        json={
            "title": "My Post",
            "body": "Content",
            "status": "draft",
            "tags": [],
        },
        headers={"X-User-Id": "user1"},
    )
    assert resp.status_code == 200
    post_id = resp.json()["id"]

    resp = client.delete(f"/posts/{post_id}", headers={"X-User-Id": "user2"})
    assert resp.status_code == 403
    body = resp.json()
    assert body["title"] == "Forbidden"
    assert "own posts" in body["detail"].lower()


def test_invalid_status_filter():
    """Негативный тест: недопустимый статус в фильтре."""
    resp = client.get("/posts?status=invalid_status")
    assert resp.status_code == 400
    body = resp.json()
    assert body["title"] == "Invalid Status"
    detail_lower = (
        body["detail"].lower() if isinstance(body["detail"], str) else str(body["detail"]).lower()
    )
    assert "draft" in detail_lower and "published" in detail_lower


def test_anonymous_post_creation_blocked():
    """Негативный тест: анонимный пользователь не может создавать посты (NFR-01, ADR-002)."""
    resp = client.post(
        "/posts",
        json={
            "title": "Anonymous Post",
            "body": "This should not work",
            "status": "draft",
            "tags": [],
        },
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["title"] == "Authentication Required"
    assert "authentication required" in body["detail"].lower()

    resp = client.post(
        "/posts",
        json={
            "title": "Anonymous Post",
            "body": "This should not work either",
            "status": "draft",
            "tags": [],
        },
        headers={"X-User-Id": "anonymous"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["title"] == "Authentication Required"
    assert "authentication required" in body["detail"].lower()


def test_authenticated_post_creation_allowed():
    """Позитивный тест: аутентифицированный пользователь может создавать посты."""
    resp = client.post(
        "/posts",
        json={
            "title": "Authenticated Post",
            "body": "This should work",
            "status": "draft",
            "tags": ["test"],
        },
        headers={"X-User-Id": "user1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Authenticated Post"
    assert body["user_id"] == "user1"


def test_rate_limit_reset_on_success():
    """Позитивный тест: rate limit сбрасывается при успешной аутентификации."""
    from app.src.rate_limit import _rate_limit_store

    _rate_limit_store.clear()
    for _ in range(3):
        resp = client.post("/login", json={"username": "admin_reset", "password": "wrongpwd"})
        assert resp.status_code == 401

    resp = client.post("/login", json={"username": "admin_reset", "password": "password123"})
    assert resp.status_code == 200

    resp = client.post("/login", json={"username": "admin_reset", "password": "wrongpwd"})
    assert resp.status_code == 401
    assert resp.status_code != 429


def test_create_access_token_default_expiry():
    """Тест создания JWT токена с дефолтным временем жизни."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0

    # Проверяем, что токен можно верифицировать
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["iss"] == "simple-blog"
    assert payload["aud"] == "simple-blog-users"


def test_create_access_token_custom_expiry():
    """Тест создания JWT токена с кастомным временем жизни."""
    data = {"sub": "testuser"}
    expires_delta = timedelta(minutes=30)
    token = create_access_token(data, expires_delta)

    assert isinstance(token, str)

    # Проверяем payload
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"


def test_verify_token_valid():
    """Тест верификации валидного токена."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "testuser"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_token_expired():
    """Тест верификации истекшего токена."""
    data = {"sub": "testuser"}
    # Создаем токен, который истек 1 час назад
    expires_delta = timedelta(hours=-1)
    token = create_access_token(data, expires_delta)

    payload = verify_token(token)
    assert payload is None  # Истекший токен должен вернуть None


def test_verify_token_invalid():
    """Тест верификации невалидного токена."""
    invalid_token = "invalid.jwt.token"

    payload = verify_token(invalid_token)
    assert payload is None


def test_get_current_user_valid_token():
    """Тест получения пользователя из валидного токена."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    user = get_current_user(token)
    assert user == "testuser"


def test_get_current_user_invalid_token():
    """Тест получения пользователя из невалидного токена."""
    invalid_token = "invalid.jwt.token"

    user = get_current_user(invalid_token)
    assert user is None
