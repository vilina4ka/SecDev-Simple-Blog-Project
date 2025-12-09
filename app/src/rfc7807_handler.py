import logging
import re
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b\d{10,}\b")
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
PASSWORD_PATTERN = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|key)\s*[:=]\s*['\"]?([^'\"]+)['\"]?"
)


def mask_pii(text: str) -> str:
    if not text:
        return text

    text = JWT_PATTERN.sub("JWT_TOKEN_MASKED", text)

    # Маскируем пароли и секреты (после JWT, чтобы не перехватывать JWT токены)
    text = PASSWORD_PATTERN.sub(r"\1: ***MASKED***", text)

    text = EMAIL_PATTERN.sub(lambda m: f"{m.group(0)[:3]}***@{m.group(0).split('@')[1]}", text)

    text = PHONE_PATTERN.sub(lambda m: f"{m.group(0)[:3]}***{m.group(0)[-2:]}", text)

    return text


def safe_log(level: int, message: str, correlation_id: Optional[str] = None, **kwargs):
    masked_message = mask_pii(message)
    masked_kwargs = {}

    # Список ключей, значения которых всегда должны маскироваться
    sensitive_keys = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "key",
        "jwt",
        "access_token",
        "refresh_token",
        "username",
    }

    for key, value in kwargs.items():
        if isinstance(value, str):
            if key.lower() in sensitive_keys:
                # Для чувствительных ключей всегда маскируем значение
                masked_kwargs[key] = "***MASKED***"
            else:
                masked_kwargs[key] = mask_pii(value)
        else:
            masked_kwargs[key] = value

    # Добавляем correlation_id в сообщение
    cid = correlation_id or "N/A"
    if masked_kwargs:
        kwargs_str = ", ".join(f"{k}={v}" for k, v in masked_kwargs.items())
        full_message = f"[correlation_id={cid}] - {masked_message} - {kwargs_str}"
    else:
        full_message = f"[correlation_id={cid}] - {masked_message}"

    logger.log(level, full_message)


def problem(
    status: int,
    title: str,
    detail: Union[str, Dict[str, Any]],
    type_: str = "about:blank",
    correlation_id: Optional[str] = None,
    instance: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    log_error: bool = True,
):
    if correlation_id is None:
        correlation_id = str(uuid4())

    payload: Dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "correlation_id": correlation_id,
    }

    if instance:
        payload["instance"] = instance

    if extras:
        payload.update(extras)

    if log_error and status >= 500:
        safe_log(
            logging.ERROR,
            "Internal server error",
            correlation_id=correlation_id,
            error_title=title,
            status=status,
            instance=instance,
        )

    return JSONResponse(payload, status_code=status, headers={"X-Correlation-ID": correlation_id})
