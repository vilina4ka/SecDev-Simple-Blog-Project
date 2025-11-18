"""Тесты для Pydantic схем и валидации данных."""

import pytest
from pydantic import ValidationError

from app.src.schemas import (
    ItemCreate,
    PostCreate,
    PostUpdate,
    UserRegister,
    normalize_unicode,
    validate_tag,
)


def test_normalize_unicode_basic():
    """Тест базовой нормализации unicode."""
    # Обычный текст
    assert normalize_unicode("hello world") == "hello world"

    # Текст с пробелами
    assert normalize_unicode("  hello  ") == "hello"

    # Пустая строка
    assert normalize_unicode("") == ""

    # None (если передан)
    assert normalize_unicode(None) is None


def test_normalize_unicode_control_chars():
    """Тест удаления управляющих символов."""
    # Текст с управляющими символами
    text_with_controls = "hello\x00\x01world\x0a"
    normalized = normalize_unicode(text_with_controls)
    # Управляющие символы должны быть удалены
    assert "\x00" not in normalized
    assert "\x01" not in normalized
    assert "\n" not in normalized  # \n тоже удаляется


def test_user_register_valid():
    """Тест валидной регистрации пользователя."""
    data = {"username": "testuser", "password": "password123"}
    user = UserRegister(**data)

    assert user.username == "testuser"
    assert user.password == "password123"


def test_user_register_username_too_short():
    """Тест: username слишком короткий."""
    data = {"username": "ab", "password": "password123"}

    with pytest.raises(ValidationError) as exc_info:
        UserRegister(**data)

    assert "String should have at least 3 characters" in str(exc_info.value)


def test_user_register_username_too_long():
    """Тест: username слишком длинный."""
    data = {"username": "a" * 51, "password": "password123"}

    with pytest.raises(ValidationError) as exc_info:
        UserRegister(**data)

    assert "String should have at most 50 characters" in str(exc_info.value)


def test_user_register_password_too_short():
    """Тест: password слишком короткий."""
    data = {"username": "testuser", "password": "12345"}

    with pytest.raises(ValidationError) as exc_info:
        UserRegister(**data)

    assert "String should have at least 6 characters" in str(exc_info.value)


def test_user_register_password_too_long():
    """Тест: password слишком длинный."""
    data = {"username": "testuser", "password": "a" * 101}

    with pytest.raises(ValidationError) as exc_info:
        UserRegister(**data)

    assert "String should have at most 100 characters" in str(exc_info.value)


def test_item_create_valid():
    """Тест валидного создания элемента."""
    data = {"name": "Test Item"}
    item = ItemCreate(**data)

    assert item.name == "Test Item"


def test_item_create_name_empty():
    """Тест: пустое имя элемента."""
    data = {"name": ""}

    with pytest.raises(ValidationError) as exc_info:
        ItemCreate(**data)

    assert "String should have at least 1 character" in str(exc_info.value)


def test_item_create_name_too_long():
    """Тест: имя элемента слишком длинное."""
    data = {"name": "a" * 101}

    with pytest.raises(ValidationError) as exc_info:
        ItemCreate(**data)

    assert "String should have at most 100 characters" in str(exc_info.value)


def test_item_create_name_normalized():
    """Тест нормализации имени элемента."""
    # Имя с управляющими символами
    data = {"name": "Test\x00Item\x01"}
    item = ItemCreate(**data)

    # Управляющие символы должны быть удалены
    assert "\x00" not in item.name
    assert "\x01" not in item.name
    assert "Test" in item.name
    assert "Item" in item.name


def test_post_create_valid():
    """Тест валидного создания поста."""
    data = {
        "title": "Test Post",
        "body": "This is a test post content.",
        "status": "draft",
        "tags": ["test", "blog"],
    }
    post = PostCreate(**data)

    assert post.title == "Test Post"
    assert post.body == "This is a test post content."
    assert post.status == "draft"
    assert post.tags == ["test", "blog"]


def test_post_create_title_too_long():
    """Тест: заголовок поста слишком длинный."""
    data = {"title": "a" * 257, "body": "Content", "status": "draft"}

    with pytest.raises(ValidationError) as exc_info:
        PostCreate(**data)

    assert "String should have at most 256 characters" in str(exc_info.value)


def test_post_create_body_too_long():
    """Тест: тело поста слишком длинное."""
    data = {"title": "Title", "body": "a" * 2001, "status": "draft"}

    with pytest.raises(ValidationError) as exc_info:
        PostCreate(**data)

    assert "String should have at most 2000 characters" in str(exc_info.value)


def test_post_create_invalid_status():
    """Тест: невалидный статус поста."""
    data = {"title": "Title", "body": "Content", "status": "invalid_status"}

    with pytest.raises(ValidationError) as exc_info:
        PostCreate(**data)

    assert "String should match pattern" in str(exc_info.value)


def test_post_update_partial():
    """Тест частичного обновления поста."""
    # Можно обновлять только часть полей
    data = {"status": "published"}
    update = PostUpdate(**data)

    assert update.status == "published"
    assert update.title is None
    assert update.body is None
    assert update.tags is None


def test_validate_tag_valid():
    """Тест валидации корректного тега."""
    assert validate_tag("python") == "python"
    assert validate_tag("python-3") == "python-3"
    assert validate_tag("test_tag") == "test_tag"


def test_validate_tag_invalid():
    """Тест валидации некорректного тега."""
    with pytest.raises(ValueError, match="tag must not be empty"):
        validate_tag("")

    with pytest.raises(ValueError, match="tag can only contain"):
        validate_tag("tag with spaces")

    with pytest.raises(ValueError, match="tag can only contain"):
        validate_tag("tag@symbol")

    with pytest.raises(ValueError, match="tag can only contain"):
        validate_tag("tag#symbol")
