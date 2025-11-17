import unicodedata
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def normalize_unicode(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if unicodedata.category(c)[0] != "C" or c in "\n\r\t ")
    return text.strip()


class ItemCreate(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Название элемента (1-100 символов)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        normalized = normalize_unicode(v)
        if not normalized:
            raise ValueError("name must not be empty after normalization")
        if len(normalized) > 100:
            raise ValueError("name must be at most 100 characters")
        return normalized


class UserRegister(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Имя пользователя (3-50 символов)",
    )
    password: str = Field(
        min_length=6,
        max_length=100,
        description="Пароль (6-100 символов)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        normalized = normalize_unicode(v)
        if not normalized:
            raise ValueError("username must not be empty after normalization")
        if len(normalized) < 3:
            raise ValueError("username must be at least 3 characters")
        if len(normalized) > 50:
            raise ValueError("username must be at most 50 characters")
        if not all(c.isalnum() or c in "-_." for c in normalized):
            raise ValueError(
                "username can only contain letters, numbers, hyphens, underscores and dots"
            )
        return normalized.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        if len(v) > 100:
            raise ValueError("password must be at most 100 characters")
        return v


class UserLogin(BaseModel):
    """Схема для входа пользователя."""

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Имя пользователя (3-50 символов)",
    )
    password: str = Field(
        min_length=6,
        max_length=100,
        description="Пароль (6-100 символов)",
    )


def validate_tag(tag: str) -> str:
    if not tag:
        raise ValueError("tag must not be empty")

    normalized = normalize_unicode(tag)
    if not normalized:
        raise ValueError("tag must not be empty after normalization")

    sql_patterns = [
        "'",
        '"',
        ";",
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
        "exec",
        "union",
        "select",
    ]
    tag_lower = normalized.lower()
    for pattern in sql_patterns:
        if pattern in tag_lower:
            raise ValueError("tag contains invalid characters")

    if not all(c.isalnum() or c in "-_" for c in normalized):
        raise ValueError("tag can only contain letters, numbers, hyphens and underscores")

    if len(normalized) > 50:
        raise ValueError("tag must be at most 50 characters")

    return normalized.lower()


class PostCreate(BaseModel):

    title: str = Field(
        min_length=1,
        max_length=256,
        description="Заголовок поста (1-256 символов)",
    )
    body: str = Field(
        min_length=1,
        max_length=2000,
        description="Содержимое поста (1-2000 символов)",
    )
    status: str = Field(
        default="draft",
        pattern="^(draft|published)$",
        description="Статус поста: draft или published",
    )
    tags: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Список тегов (максимум 10 тегов)",
    )

    @field_validator("title", "body")
    @classmethod
    def validate_text_field(cls, v: str) -> str:
        normalized = normalize_unicode(v)
        if not normalized:
            raise ValueError("field must not be empty after normalization")
        return normalized

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v: str) -> str:
        if len(v) > 256:
            raise ValueError("title must be at most 256 characters")
        return v

    @field_validator("body")
    @classmethod
    def validate_body_length(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("body must be at most 2000 characters")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError("maximum 10 tags allowed")
        unique_tags = []
        for tag in v:
            validated_tag = validate_tag(tag)
            if validated_tag not in unique_tags:
                unique_tags.append(validated_tag)
        return unique_tags


class PostUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Заголовок поста (1-256 символов)",
    )
    body: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description="Содержимое поста (1-2000 символов)",
    )
    status: Optional[str] = Field(
        default=None,
        pattern="^(draft|published)$",
        description="Статус поста: draft или published",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Список тегов (максимум 10 тегов)",
    )

    @field_validator("title", "body")
    @classmethod
    def validate_text_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        normalized = normalize_unicode(v)
        if not normalized:
            raise ValueError("field must not be empty after normalization")
        return normalized

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        if len(v) > 10:
            raise ValueError("maximum 10 tags allowed")
        unique_tags = []
        for tag in v:
            validated_tag = validate_tag(tag)
            if validated_tag not in unique_tags:
                unique_tags.append(validated_tag)
        return unique_tags
