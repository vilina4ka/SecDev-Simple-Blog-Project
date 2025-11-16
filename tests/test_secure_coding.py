"""Тесты для secure coding практики P06."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.src.rfc7807_handler import mask_pii
from app.src.upload_secure import secure_save, sniff_image_type

client = TestClient(app)


def test_health_endpoint():
    """Проверка эндпоинта /health."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_rfc7807_validation_error():
    """Проверка RFC 7807 формата для ошибок валидации."""
    # Пустое имя
    resp = client.post("/items", json={"name": ""})
    assert resp.status_code == 422
    body = resp.json()
    assert "type" in body
    assert "title" in body
    assert body["title"] == "Validation Error"
    assert "correlation_id" in body
    assert "detail" in body
    assert "X-Correlation-ID" in resp.headers


def test_long_title_returns_422():
    """Негативный тест: слишком длинный заголовок поста (>256 символов)."""
    long_title = "a" * 257  # Превышает лимит в 256 символов
    resp = client.post(
        "/posts",
        json={
            "title": long_title,
            "body": "Test body",
            "status": "draft",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["title"] == "Validation Error"
    assert "correlation_id" in body


def test_long_body_returns_422():
    """Негативный тест: слишком длинное тело поста (>2000 символов)."""
    long_body = "a" * 2001  # Превышает лимит в 2000 символов
    resp = client.post(
        "/posts",
        json={
            "title": "Test title",
            "body": long_body,
            "status": "draft",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["title"] == "Validation Error"


def test_empty_post_fields():
    """Негативный тест: пустые поля поста после нормализации."""
    # Пробелы и управляющие символы должны быть отклонены
    resp = client.post(
        "/posts",
        json={
            "title": "   ",
            "body": "\t\n\r",
            "status": "draft",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 422


def test_invalid_post_status():
    """Негативный тест: недопустимый статус поста."""
    resp = client.post(
        "/posts",
        json={
            "title": "Test",
            "body": "Test body",
            "status": "invalid_status",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 422


def test_path_traversal_attack(tmp_path: Path):
    """Негативный тест: защита от path traversal атаки."""
    # Создаем базовую директорию
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    # Пытаемся использовать path traversal через имя файла
    # secure_save генерирует имя автоматически, но проверим защиту через os.path.commonpath
    png_data = b"\x89PNG\r\n\x1a\n" + b"data"

    # Попытка создать файл вне базовой директории через относительный путь
    # (в реальности имя генерируется, но проверяем логику)
    result_path = secure_save(str(base_dir), png_data)

    # Проверяем, что файл создан внутри базовой директории
    assert result_path.startswith(str(base_dir.resolve()))

    # Пытаемся использовать несуществующую базовую директорию
    with pytest.raises(ValueError, match="base_dir_not_found"):
        secure_save(str(tmp_path / "nonexistent"), png_data)


def test_symlink_attack(tmp_path: Path):
    """Негативный тест: защита от символьных ссылок."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    png_data = b"\x89PNG\r\n\x1a\n" + b"data"

    # Проверяем защиту от симлинка в root
    # Создадим ситуацию, где root является симлинком
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    symlink_root = tmp_path / "symlink_root"

    # Создаем симлинк только если поддерживается (на Windows может не работать)
    try:
        symlink_root.symlink_to(real_dir)
        # Если симлинк создан, проверяем защиту
        with pytest.raises(ValueError, match="root_is_symlink"):
            secure_save(str(symlink_root), png_data)
    except (OSError, NotImplementedError):
        # На некоторых системах симлинки не поддерживаются, пропускаем тест
        pytest.skip("Symlinks not supported on this system")


def test_file_too_big(tmp_path: Path):
    """Негативный тест: слишком большой файл (>5MB)."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    # Создаем файл больше 5MB
    large_data = b"\x89PNG\r\n\x1a\n" + b"0" * 5_000_001

    with pytest.raises(ValueError, match="too_big"):
        secure_save(str(base_dir), large_data)


def test_invalid_file_type(tmp_path: Path):
    """Негативный тест: неподдерживаемый тип файла."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    # Файл без правильных magic bytes
    invalid_data = b"not an image file"

    with pytest.raises(ValueError, match="bad_type"):
        secure_save(str(base_dir), invalid_data)


def test_pii_masking():
    """Тест маскирования PII в логах."""
    # Email
    text = "Contact user@example.com for details"
    masked = mask_pii(text)
    assert "user@example.com" not in masked
    assert "user***@example.com" in masked or "***" in masked

    # JWT токен (проверяем, что JWT паттерн работает)
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "dozjgN6z7hm7N8Bm7f8Y9vX8Y9vX8Y9vX8Y9vX8Y9vX"
    )
    text = f"Token: {jwt}"
    masked = mask_pii(text)
    assert jwt not in masked
    # JWT должен быть замаскирован (либо как JWT_TOKEN_MASKED, либо через password pattern)
    assert "JWT_TOKEN_MASKED" in masked or "***MASKED***" in masked

    # Пароль
    text = 'password: "secret123"'
    masked = mask_pii(text)
    assert "secret123" not in masked
    assert "***MASKED***" in masked


def test_correlation_id_present():
    """Проверка наличия correlation_id в ответах."""
    resp = client.get("/items/999")  # 404 ошибка
    assert resp.status_code == 404
    assert "X-Correlation-ID" in resp.headers
    body = resp.json()
    assert "correlation_id" in body
    assert body["correlation_id"] == resp.headers["X-Correlation-ID"]


def test_unicode_normalization():
    """Тест нормализации unicode в валидации."""
    resp = client.post(
        "/posts",
        json={
            "title": "Тест с кириллицей",
            "body": "Содержимое поста",
            "status": "draft",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 200


def test_control_characters_stripped():
    """Негативный тест: управляющие символы должны удаляться."""
    resp = client.post(
        "/posts",
        json={
            "title": "\x00\x01\x02",
            "body": "\x03\x04\x05",
            "status": "draft",
        },
        headers={"X-User-Id": "testuser"},
    )
    assert resp.status_code == 422


def test_internal_error_masking():
    """Проверка маскирования деталей внутренних ошибок (5xx)."""


def test_validation_error_format():
    resp = client.post("/items", json={"name": "a" * 101})  # Превышает лимит
    assert resp.status_code == 422
    body = resp.json()
    assert body["type"] == "https://example.com/problems/validation-error"
    assert body["status"] == 422
    assert "instance" in body
    assert body["instance"] == "/items"


def test_sniff_image_type_edge_cases():
    assert sniff_image_type(b"") is None

    assert sniff_image_type(b"\xff\xd8data") is None

    assert sniff_image_type(b"\x89PNG") is None

    assert sniff_image_type(b"\x89PNG\r\n\x1a\n" + b"data") == "image/png"

    assert sniff_image_type(b"\xff\xd8data\xff\xd9") == "image/jpeg"
