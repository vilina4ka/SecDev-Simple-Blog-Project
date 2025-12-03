# SecDev Course — Simple Blog Project

![CI](https://github.com/vilina4ka/Secdev-Simple-Blog-Project/actions/workflows/ci.yml/badge.svg)

## Описание проекта
**Simple Blog** — веб-приложение на **FastAPI**, реализующее приватный блог с безопасным доступом.
После входа пользователь может:
- создавать посты;
- редактировать и удалять **только свои** посты;
- добавлять теги;
- фильтровать публикации по статусу и тегу.

**Stretch:** публичная лента (read-only) позволяет просматривать опубликованные посты других пользователей.

---

## Проблематика
Во многих блоговых платформах контент по умолчанию публичен, что не всегда подходит для корпоративных или учебных целей, так как содержание постов должно быть закрытым. Необходима закрытая блог-система, где пользователи могут создавать и редактировать только свои посты, а чужие данные защищены. При этом полезно будет посмореть посты других пользователей, а значит в в системе должна быть публичная лента (read-only).

---

## Сущности
- **User** — пользователь системы.
- **Post** — публикация (`title`, `body`, `status`).
- **Tag** — тег, связанный с постами.


---

## Фокус на безопасность
- **Аутентификация и авторизация (AuthN/AuthZ)**.
- **Owner-only access** — редактировать и удалять можно только свои посты.
- Проверка длины контента и валидация данных.

---

## Технические требования
- Язык: **Python 3.11+**
- Фреймворк: **FastAPI**
- База данных: SQLite / PostgreSQL
- Контейнеризация: Docker, docker-compose
- Тестирование: pytest
- Линтинг: ruff, black, isort
- Прехуки: pre-commit hooks
- CI/CD: GitHub Actions

---

## Технологический стек
- Backend: FastAPI
- База данных: SQLite / PostgreSQL
- Тесты: pytest
- Инфраструктура: Docker, docker-compose
- Код-стайл: ruff, black, isort, pre-commit
- CI/CD: GitHub Actions

---

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload
```

## JWT Аутентификация

Проект поддерживает JWT токены для аутентификации:

**Установка PyJWT:**
```bash
pip install PyJWT==2.8.0
```

**Использование:**
1. `POST /login` → получает JWT токен (TTL: 1 час)
2. `Authorization: Bearer <token>` в заголовках запросов

**Пример:**
```bash
curl -X POST "http://127.0.0.1:8000/login?username=admin&password=password123"

curl -H "Authorization: Bearer eyJ..." http://127.0.0.1:8000/posts
```

---

## Доменные сценарии

* Пользователь создаёт пост: **POST /posts**
* Получает список своих постов: **GET /posts?status=**
* Фильтрует посты по тегам: **GET /posts?tag=fastapi**
* Редактирует и удаляет только свои посты (owner-only access)

---

## Ритуал перед PR

```bash
ruff check --fix .
black .
isort .
pytest -q
pre-commit run --all-files
```

---

## Запуск тестов

```bash
pytest -q
```
---

## CI

В репозитории настроен workflow **CI (GitHub Actions)**, который выполняет:

* установку зависимостей,
* линтинг (`ruff`, `black`, `isort`),
* юнит-тесты,
* `pre-commit run --all-files`.

CI является *required check* для ветки `main`.
Badge добавится автоматически после загрузки шаблона в GitHub.

---

## Контейнеры

```bash
docker build -t secdev-blog .
docker run --rm -p 8000:8000 secdev-blog
# или
docker compose up --build
```

---

## Примерная структура проекта

```
app/
 ├── main.py
 ├── models.py
 ├── routers/
 │   └── posts.py
 ├── schemas/
 │   └── post.py
 └── core/
     └── auth.py
tests/
 └── test_posts.py
```

**Конфиги**: `.env`, `.env.example`

---

## Эндпойнты

- `CRUD /posts`
- `GET /posts?status=&tag=`
- `GET /posts/public` — публичная лента (read-only, stretch)

### Формат ошибок

```json
{
  "error": {
    "code": "not_found",
    "message": "item not found"
  }
}
```

---

См. также:

* [`SECURITY.md`](SECURITY.md)
* [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
* [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

## Evidence & Security Automation

- Workflow **Security - SBOM & SCA** (`.github/workflows/ci-sbom-sca.yml`) генерирует CycloneDX SBOM и отчёты SCA при каждом push/PR.
- Артефакты сохраняются в `EVIDENCE/P09/` (`sbom.json`, `sca_report.json`, `sca_summary.md`).
- Исключения и временные ваиверы документируются в `policy/waivers.yml` на основе политики из `project/69_sbom-vuln-mgmt.md`.
