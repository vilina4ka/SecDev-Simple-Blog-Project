# Быстрый старт проекта P06

## Установка и запуск

```bash
# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Установить зависимости
pip install -r requirements.txt -r requirements-dev.txt

# Запустить сервер
uvicorn app.main:app --reload
```

**API документация:** http://127.0.0.1:8000/docs

## API Эндпоинты

### Аутентификация
- `POST /register` — регистрация пользователя
- `POST /login` — вход (возвращает JWT токен)

### Посты (требуют JWT)
- `POST /posts` — создать пост
- `GET /posts` — получить свои посты
- `GET /posts/{id}` — получить пост по ID
- `PATCH /posts/{id}` — обновить пост
- `DELETE /posts/{id}` — удалить пост

### Публичный доступ
- `GET /posts/public` — опубликованные посты всех пользователей
- `GET /health` — проверка работоспособности

## Работа с API

### 1. Регистрация и вход
```bash
# Регистрация
curl -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'

# Вход (получить токен)
TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/login?username=testuser&password=password123" \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

### 2. Работа с постами
```bash
# Создать пост
curl -X POST http://127.0.0.1:8000/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Мой пост", "body": "Содержимое", "status": "draft"}'

# Получить свои посты
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/posts

# Обновить пост (ID=1)
curl -X PATCH http://127.0.0.1:8000/posts/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "published"}'

# Удалить пост
curl -X DELETE http://127.0.0.1:8000/posts/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Тестирование

```bash
# Все тесты
pytest -q

# Тесты безопасности P06
pytest tests/test_p06_secure_controls.py -v

# С покрытием
pytest --cov=app --cov-report=term-missing
```

## Docker (P07)

### Production запуск
```bash
# Сборка и запуск production контейнера
make build
make up

# Или напрямую
docker compose --profile production up -d
```

### Development режим
```bash
# Development с hot-reload
make dev

# Или напрямую
docker compose --profile dev up
```

### Проверка работоспособности
```bash
# Health check
curl http://localhost:8000/health
# {"status": "ok"}

# API документация
open http://localhost:8000/docs
```

### Security проверки
```bash
# Линтинг Dockerfile
make docker-lint

# Сканирование уязвимостей
make image-scan

# Проверка пользователя
docker exec $(docker ps -q) id -u  # Должен вернуть 1000
```

### Дополнительные команды
```bash
# Просмотр логов
make logs

# Очистка
make clean

# Все доступные команды
make help
```

## Quality Gate

```bash
# Проверка кода
ruff check .
black --check .
isort --check-only .

# Исправление
ruff check --fix .
black .
isort .
```
