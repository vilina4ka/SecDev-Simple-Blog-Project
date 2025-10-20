# NFR — BDD-сценарии безопасности — Simple Blog

Здесь приведены сценарии проверки ключевых NFR для Simple Blog.
Формат: **Gherkin (Given / When / Then)**.

---

## Feature: JWT Authentication (NFR-01)

### Scenario: Успешная аутентификация
```gherkin
Given зарегистрированный пользователь с логином "user1" и валидным паролем
When он отправляет POST /login
Then получает ответ 200 и JWT-токен, срок действия ≤ 1 час
```

### Scenario: Ошибка при неверных учетных данных
```gherkin
Given пользователь с логином "user1" и неверным паролем
When он отправляет POST /login
Then получает ответ 401 Unauthorized
```

### Scenario: Доступ без токена запрещён
```gherkin
Given неавторизованный пользователь
When он запрашивает GET /posts (защищённый эндпойнт)
Then получает ответ 401 Unauthorized
```

### Scenario: Доступ с истёкшим токеном
```gherkin
Given пользователь авторизован с JWT-токеном старше 1 часа
When он отправляет GET /posts
Then получает ответ 401 Unauthorized
```

---

## Feature: Owner-only Authorization (NFR-02)

### Scenario: Редактирование собственного поста
```gherkin
Given пользователь "user1" авторизован и владеет постом
When он пытается PATCH /posts/{post_id}
Then получает ответ 200 OK
```

### Scenario: Редактирование чужого поста запрещено
```gherkin
Given пользователь "user1" авторизован
When он пытается PATCH /posts/{post_id} чужого поста
Then получает ответ 403 Forbidden
```

---

## Feature: Input Data Validation (NFR-04)

### Scenario: Создание поста с пустым заголовком
```gherkin
Given авторизованный пользователь
When он отправляет POST /posts с пустым "title"
Then получает ответ 422 Unprocessable Entity
```

### Scenario: Создание поста с слишком длинным заголовком
```gherkin
Given авторизованный пользователь
When он отправляет POST /posts с "title" длиной более 256 символов
Then получает ответ 422 Unprocessable Entity
```

### Scenario: Создание поста с слишком длинным телом
```gherkin
Given авторизованный пользователь
When он отправляет POST /posts с "body" длиной более 2000 символов
Then получает ответ 422 Unprocessable Entity
```

---

## Feature: Fast API Response (NFR-08)

### Scenario: Нормальная нагрузка
```gherkin
Given обычный поток запросов (до ожидаемого RPS)
When пользователь запрашивает GET /posts
Then 95% ответов приходят не дольше 500ms
```

### Scenario: Высокая нагрузка (негативный)
```gherkin
Given экстремальное количество одновременных запросов
When пользователь запрашивает GET /posts
Then система может вернуть 503 Service Unavailable
```
