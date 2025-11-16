from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_user():
    """Тест регистрации нового пользователя."""
    data = {"username": "testuser_api", "password": "password123"}

    resp = client.post("/register", json=data)
    assert resp.status_code == 200

    body = resp.json()
    assert body["username"] == "testuser_api"
    assert body["message"] == "User registered successfully"


def test_login_success():
    """Тест успешного входа."""
    # Сначала регистрируем
    client.post("/register", json={"username": "login_test", "password": "password123"})

    # Затем входим
    resp = client.post("/login?username=login_test&password=password123")
    assert resp.status_code == 200

    body = resp.json()
    assert body["username"] == "login_test"
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password():
    """Тест входа с неправильным паролем."""
    resp = client.post("/login?username=nonexistent&password=wrong")
    assert resp.status_code == 401


def test_create_post_authenticated():
    """Тест создания поста авторизованным пользователем."""
    # Регистрируем и получаем токен
    client.post("/register", json={"username": "post_creator", "password": "password123"})
    login_resp = client.post("/login?username=post_creator&password=password123")
    token = login_resp.json()["access_token"]

    # Создаем пост
    post_data = {
        "title": "Test Post",
        "body": "This is a test post content.",
        "status": "draft",
        "tags": ["test"],
    }

    resp = client.post("/posts", json=post_data, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["title"] == "Test Post"
    assert body["body"] == "This is a test post content."
    assert body["status"] == "draft"
    assert body["tags"] == ["test"]
    assert body["user_id"] == "post_creator"
    assert "id" in body


def test_create_post_unauthenticated():
    """Тест создания поста без аутентификации."""
    post_data = {"title": "Test Post", "body": "Content", "status": "draft"}

    resp = client.post("/posts", json=post_data)
    assert resp.status_code == 401


def test_get_user_posts():
    """Тест получения постов пользователя."""
    # Регистрируем и получаем токен
    client.post("/register", json={"username": "posts_viewer", "password": "password123"})
    login_resp = client.post("/login?username=posts_viewer&password=password123")
    token = login_resp.json()["access_token"]

    # Создаем пост
    post_data = {"title": "My Post", "body": "Content", "status": "draft"}
    client.post("/posts", json=post_data, headers={"Authorization": f"Bearer {token}"})

    # Получаем посты
    resp = client.get("/posts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    data = resp.json()
    assert "posts" in data
    assert "count" in data
    assert data["count"] >= 1

    posts = data["posts"]
    assert isinstance(posts, list)
    assert len(posts) >= 1

    # Проверяем наш пост
    found_post = None
    for post in posts:
        if post["title"] == "My Post":
            found_post = post
            break

    assert found_post is not None
    assert found_post["user_id"] == "posts_viewer"


def test_get_post_by_id():
    """Тест получения поста по ID."""
    # Регистрируем и получаем токен
    client.post("/register", json={"username": "post_getter", "password": "password123"})
    login_resp = client.post("/login?username=post_getter&password=password123")
    token = login_resp.json()["access_token"]

    # Создаем пост
    post_data = {"title": "Post to Get", "body": "Content", "status": "draft"}
    create_resp = client.post(
        "/posts", json=post_data, headers={"Authorization": f"Bearer {token}"}
    )
    post_id = create_resp.json()["id"]

    # Получаем пост по ID
    resp = client.get(f"/posts/{post_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    post = resp.json()
    assert post["id"] == post_id
    assert post["title"] == "Post to Get"
    assert post["user_id"] == "post_getter"


def test_update_own_post():
    """Тест обновления собственного поста."""
    # Регистрируем и получаем токен
    client.post("/register", json={"username": "post_updater", "password": "password123"})
    login_resp = client.post("/login?username=post_updater&password=password123")
    token = login_resp.json()["access_token"]

    # Создаем пост
    post_data = {
        "title": "Original Title",
        "body": "Original content",
        "status": "draft",
    }
    create_resp = client.post(
        "/posts", json=post_data, headers={"Authorization": f"Bearer {token}"}
    )
    post_id = create_resp.json()["id"]

    # Обновляем пост
    update_data = {"title": "Updated Title", "status": "published"}
    resp = client.patch(
        f"/posts/{post_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    updated_post = resp.json()
    assert updated_post["title"] == "Updated Title"
    assert updated_post["status"] == "published"
    assert updated_post["body"] == "Original content"  # Не изменилось


def test_update_other_user_post():
    """Тест попытки обновления чужого поста."""
    # Создаем двух пользователей с уникальными именами
    client.post("/register", json={"username": "owner_user", "password": "pass123"})
    client.post("/register", json={"username": "hacker_user", "password": "pass123"})

    # owner_user создает пост
    owner_login = client.post("/login?username=owner_user&password=pass123")
    owner_token = owner_login.json()["access_token"]

    post_data = {"title": "Owner Post", "body": "Content", "status": "draft"}
    create_resp = client.post(
        "/posts", json=post_data, headers={"Authorization": f"Bearer {owner_token}"}
    )
    post_id = create_resp.json()["id"]

    # hacker_user пытается обновить пост owner_user
    hacker_login = client.post("/login?username=hacker_user&password=pass123")
    hacker_token = hacker_login.json()["access_token"]

    update_data = {"title": "Hacked Title"}
    resp = client.patch(
        f"/posts/{post_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {hacker_token}"},
    )
    assert resp.status_code == 403  # Forbidden


def test_delete_own_post():
    """Тест удаления собственного поста."""
    # Регистрируем и получаем токен
    client.post("/register", json={"username": "post_deleter", "password": "password123"})
    login_resp = client.post("/login?username=post_deleter&password=password123")
    token = login_resp.json()["access_token"]

    # Создаем пост
    post_data = {"title": "Post to Delete", "body": "Content", "status": "draft"}
    create_resp = client.post(
        "/posts", json=post_data, headers={"Authorization": f"Bearer {token}"}
    )
    post_id = create_resp.json()["id"]

    # Удаляем пост
    resp = client.delete(f"/posts/{post_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # Проверяем, что пост удален
    get_resp = client.get(f"/posts/{post_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 404


def test_get_public_posts():
    """Тест получения публичных постов."""
    # Создаем опубликованный пост
    client.post("/register", json={"username": "public_poster", "password": "password123"})
    login_resp = client.post("/login?username=public_poster&password=password123")
    token = login_resp.json()["access_token"]

    post_data = {
        "title": "Public Post",
        "body": "This should be visible to everyone",
        "status": "published",
        "tags": ["public"],
    }
    client.post("/posts", json=post_data, headers={"Authorization": f"Bearer {token}"})

    # Получаем публичные посты (без аутентификации)
    resp = client.get("/posts/public")
    assert resp.status_code == 200

    data = resp.json()
    assert "posts" in data
    assert "count" in data

    posts = data["posts"]
    assert isinstance(posts, list)

    # Ищем наш пост
    found_post = None
    for post in posts:
        if post["title"] == "Public Post":
            found_post = post
            break

    assert found_post is not None
    assert found_post["status"] == "published"
    assert found_post["user_id"] == "public_poster"


def test_health_check():
    """Тест проверки работоспособности сервиса."""
    resp = client.get("/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "ok"
