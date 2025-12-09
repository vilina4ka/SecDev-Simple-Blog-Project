import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

# In-memory хранилище для rate limiting (в production использовать Redis)
_rate_limit_store: Dict[str, Dict[str, int]] = defaultdict(dict)

# Конфигурация rate limits
MAX_ATTEMPTS_PER_IP = 5  # Максимум попыток с одного IP
MAX_ATTEMPTS_PER_ACCOUNT = 20  # Максимум попыток на аккаунт
WINDOW_SECONDS = 60  # Окно времени в секундах (1 минута)
ACCOUNT_WINDOW_SECONDS = 3600  # Окно для аккаунта (1 час)
LOCKOUT_SECONDS = 1800  # Блокировка на 30 минут при превышении


def check_rate_limit(
    identifier: str, max_attempts: int, window: int
) -> Tuple[bool, Optional[float]]:
    now = time.time()
    now_str = str(int(now))  # Используем целое число как ключ
    key = f"{identifier}_{window}"

    attempts = _rate_limit_store[key]
    attempts_clean: Dict[str, int] = {}
    for timestamp_str, count in attempts.items():
        timestamp = float(timestamp_str)
        if now - timestamp < window:
            attempts_clean[timestamp_str] = count

    # Подсчитываем попытки в окне
    total_attempts = sum(attempts_clean.values())

    if total_attempts >= max_attempts:
        # Вычисляем время до разблокировки
        if attempts_clean:
            oldest_timestamp_str = min(attempts_clean.keys(), key=float)
            oldest_timestamp = float(oldest_timestamp_str)
            unlock_time = oldest_timestamp + window
            retry_after = max(0, unlock_time - now)
        else:
            retry_after = window
        return False, retry_after

    # Записываем текущую попытку
    attempts[now_str] = attempts.get(now_str, 0) + 1
    _rate_limit_store[key] = attempts

    return True, None


def check_ip_rate_limit(ip: str) -> Tuple[bool, Optional[float]]:
    return check_rate_limit(f"ip:{ip}", MAX_ATTEMPTS_PER_IP, WINDOW_SECONDS)


def check_account_rate_limit(username: str) -> Tuple[bool, Optional[float]]:
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
