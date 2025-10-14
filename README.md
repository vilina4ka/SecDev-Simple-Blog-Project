# SecDev Course — Simple Blog Project

Проект представляет собой **мини-блог без публичных аккаунтов**, реализованный на **FastAPI**.
Основные функции: авторизация пользователей, создание и редактирование постов, тегирование и фильтрация по статусу и тегу.

---

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload
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

Тесты используют SQLite in-memory по умолчанию.
Для интеграционных тестов можно задать переменную окружения:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/blog
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

## Структура проекта

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
**Логи**: `logs/app.log` (ротация ежедневно)

---

## Эндпойнты

* CRUD `/posts`
* `GET /posts?status=&tag=`

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
