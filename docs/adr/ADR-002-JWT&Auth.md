# ADR-002: JWT & Auth — срок жизни токена, проверка и rate-limit на /login

Дата: 2025-11-03
Статус: Accepted

## Context

NFR-01 требует: JWT валиден ≤ 1 час. Также есть риски brute-force и подмены токенов.

## Decision

1. JWT TTL (exp) — 1 час (3600s). Refresh token — отдельная операция с долгим TTL, хранится в БД и может быть отозван.
2. Использовать HS256 (HMAC) с 32+ байт секретом или предпочтительно RS256 (асимметричный).
3. На `/login` включить rate-limiting: например 5 попыток в минуту на IP + 20 попыток на account в час. Добавить lockout на 30 минут при повторных нарушениях.
4. Проверять `iat`, `exp`, `nbf` и `aud` при декодировании токена.
5. Нигде не логировать секреты/токены; в логах — только `correlation_id` и идентификатор пользователя.

## Alternatives

* Более короткий TTL (30 мин) — безопаснее, но ухудшает UX.
* Только HS256 — проще, но менее гибко.

## Consequences

* Уменьшает риск кражи и подмены токенов.

- Требует реализации refresh-токенов и изменений в клиенте.

## Security impact

Снижение риска R1, R2 (bruteforce, spoofing).

## Rollout plan

1. Ввести JWT helper `core/auth.py` с TTL=3600.
2. Добавить rate-limit middleware (или использовать внешний rate-limiter).
3. Тесты: проверка истёкшего токена, rate-limit.

## Links

- **NFR:** NFR-01 (JWT ≤ 1 час), NFR-06 (защита паролей)
- **Threat Model:** Потоки [F1 /login], [F2 /posts], [F6 Core Processing] → Риски [R1, R2, R3]
- **Тесты:** `tests/test_secure_coding.py::test_expired_jwt`, `tests/test_secure_coding.py::test_login_rate_limit`
- **RISKS.md:**
  - R1 — Брутфорс логина
  - R2 — Подмена токена / spoofing
  - R3 — Изменение чужих постов (при некорректной проверке токена)
