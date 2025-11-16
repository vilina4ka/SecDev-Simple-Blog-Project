"""Rate limiting для защиты от brute-force атак (ADR-002, NFR-01, R1)."""

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

# In-memory хранилище для rate limiting (в production использовать Redis)
_rate_limit_store: Dict[str, Dict[str, float]] = defaultdict(dict)

# Конфигурация rate limits
MAX_ATTEMPTS_PER_IP = 5  # Максимум попыток с одного IP
MAX_ATTEMPTS_PER_ACCOUNT = 20  # Максимум попыток на аккаунт
WINDOW_SECONDS = 60  # Окно времени в секундах (1 минута)
ACCOUNT_WINDOW_SECONDS = 3600  # Окно для аккаунта (1 час)
LOCKOUT_SECONDS = 1800  # Блокировка на 30 минут при превышении


def check_rate_limit(
    identifier: str, max_attempts: int, window: int
) -> Tuple[bool, Optional[float]]:
    """
    Проверяет rate limit для идентификатора.

    Args:
        identifier: IP адрес или имя аккаунта
        max_attempts: Максимальное количество попыток
        window: Окно времени в секундах

    Returns:
        Tuple[bool, Optional[float]]: (разрешено, время до разблокировки в секундах или None)
    """
    now = time.time()
    key = f"{identifier}_{window}"

    # Очищаем старые записи
    attempts = _rate_limit_store[key]
    attempts_clean = {
        timestamp: count
        for timestamp, count in attempts.items()
        if now - timestamp < window
    }

    # Подсчитываем попытки в окне
    total_attempts = sum(attempts_clean.values())

    if total_attempts >= max_attempts:
        # Вычисляем время до разблокировки
        oldest_timestamp = min(attempts_clean.keys()) if attempts_clean else now
        unlock_time = oldest_timestamp + window
        retry_after = max(0, unlock_time - now)
        return False, retry_after

    # Записываем текущую попытку
    attempts[now] = attempts.get(now, 0) + 1
    _rate_limit_store[key] = attempts

    return True, None


def check_ip_rate_limit(ip: str) -> Tuple[bool, Optional[float]]:
    """
    Проверяет rate limit для IP адреса.

    Args:
        ip: IP адрес клиента

    Returns:
        Tuple[bool, Optional[float]]: (разрешено, время до разблокировки)
    """
    return check_rate_limit(f"ip:{ip}", MAX_ATTEMPTS_PER_IP, WINDOW_SECONDS)


def check_account_rate_limit(username: str) -> Tuple[bool, Optional[float]]:
    """
    Проверяет rate limit для аккаунта.

    Args:
        username: Имя пользователя

    Returns:
        Tuple[bool, Optional[float]]: (разрешено, время до разблокировки)
    """
    return check_rate_limit(
        f"account:{username}", MAX_ATTEMPTS_PER_ACCOUNT, ACCOUNT_WINDOW_SECONDS
    )


def reset_rate_limit(identifier: str):
    """Сбрасывает rate limit для идентификатора (при успешной аутентификации)."""
    for key in list(_rate_limit_store.keys()):
        if key.startswith(f"ip:{identifier}") or key.startswith(
            f"account:{identifier}"
        ):
            del _rate_limit_store[key]
