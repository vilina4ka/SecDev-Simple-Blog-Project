# ADR-003: Input validation — Pydantic schemas, length limits, normalization

Дата: 2025-11-03
Статус: Accepted

## Context

NFR-04/NFR-05 требуют строгой проверки полей постов (title ≤256, body ≤2000) и корректного ответа при нарушении схемы.

## Decision

1. Использовать Pydantic для схем входных данных с ограничениями: `constr(max_length=256)` для `title`, `constr(max_length=2000)` для `body`.
2. Добавить pre-validators: `strip()`, нормализация unicode (NFC), удаление управляющих символов.
3. Отдельно валидировать загружаемые файлы (если есть): magic bytes, MIME, max size.
4. В случае ошибки возвращать RFC7807 `validation_error` (ADR-001).

## Alternatives

* Выполнять валидацию вручную — больше кода, больше багов.

## Consequences

* Явное соответствие NFR-04/NFR-05.

- Потребует обновления схем.

## Security impact

Снижение риска R3/R7 (tampering / input-based attacks).

## Rollout plan

1. Обновить `schemas/post.py` или соответствующий модуль.
2. Обновить handlers, чтобы ловить `ValidationError` и конвертировать в ProblemDetails.
3. Добавить unit/BDD тесты.

## Links

- **NFR:** NFR-04 (валидация данных), NFR-05 (длина полей)
- **Threat Model:** Потоки [F2 /posts], [F3 /posts], [F6 Processing] → Риски [R3, R7, R8]
- **Тесты:**
  - `tests/test_secure_upload.py::test_secure_save_ok`
  - `tests/test_secure_upload.py::test_secure_save_too_big`
  - `tests/test_secure_upload.py::test_sniff_image_type_ok_png`
  - `tests/test_secure_upload.py::test_sniff_image_type_bad_type`
  - `tests/test_secure_coding.py::test_long_title_returns_422`
- **RISKS.md:**
  - R3 — Некорректная валидация данных
  - R7 — Искажение статистики через неверный ввод
  - R8 — Доступ к чужим данным через некорректные фильтры
