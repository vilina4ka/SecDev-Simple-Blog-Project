import logging
from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from app.core.auth import create_access_token, get_current_user
from app.src.rate_limit import check_account_rate_limit, check_ip_rate_limit, reset_rate_limit
from app.src.rfc7807_handler import problem, safe_log
from app.src.schemas import ItemCreate, PostCreate, PostUpdate, UserRegister

correlation_id_ctx: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


class CorrelationIdFilter(logging.Filter):

    def filter(self, record):
        record.correlation_id = correlation_id_ctx.get() or "N/A"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - "
    "[correlation_id=%(correlation_id)s] - %(message)s",
)
logger = logging.getLogger(__name__)
logger.addFilter(CorrelationIdFilter())

app = FastAPI(title="Simple Blog Project", version="0.1.0")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid4())
        correlation_id_ctx.set(cid)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


class JWTMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: StarletteRequest, call_next):
        auth_header = request.headers.get("Authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user_id = get_current_user(token)

        if not user_id:
            user_id = request.headers.get("X-User-Id")

        request.state.user_id = user_id

        response = await call_next(request)
        return response


app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(JWTMiddleware)


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    cid = correlation_id_ctx.get()

    if exc.status >= 500:
        detail = (
            "An internal error occurred. Please contact support with correlation_id."
        )
        safe_log(
            logging.ERROR, f"ApiError: {exc.message}", correlation_id=cid, code=exc.code
        )
    else:
        detail = exc.message
        safe_log(
            logging.WARNING,
            f"ApiError: {exc.message}",
            correlation_id=cid,
            code=exc.code,
        )

    return problem(
        status=exc.status,
        title=exc.code.replace("_", " ").title(),
        detail=detail,
        type_=f"https://example.com/problems/{exc.code}",
        correlation_id=cid,
        instance=str(request.url.path),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    cid = correlation_id_ctx.get()
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"

    if exc.status_code >= 500:
        detail = (
            "An internal error occurred. Please contact support with correlation_id."
        )
        safe_log(
            logging.ERROR,
            f"HTTPException: {exc.detail}",
            correlation_id=cid,
            status=exc.status_code,
        )
    else:
        safe_log(
            logging.WARNING,
            f"HTTPException: {exc.detail}",
            correlation_id=cid,
            status=exc.status_code,
        )

    return problem(
        status=exc.status_code,
        title="HTTP Error",
        detail=detail,
        type_="https://example.com/problems/http-error",
        correlation_id=cid,
        instance=str(request.url.path),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cid = correlation_id_ctx.get()

    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors[field] = error["msg"]

    safe_log(logging.INFO, f"Validation error: {errors}", correlation_id=cid)

    return problem(
        status=422,
        title="Validation Error",
        detail=errors,
        type_="https://example.com/problems/validation-error",
        correlation_id=cid,
        instance=str(request.url.path),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    cid = correlation_id_ctx.get()

    safe_log(
        logging.ERROR,
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        correlation_id=cid,
        exception_type=type(exc).__name__,
    )

    return problem(
        status=500,
        title="Internal Server Error",
        detail="An internal error occurred. Please contact support with correlation_id.",
        type_="https://example.com/problems/internal-error",
        correlation_id=cid,
        instance=str(request.url.path),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


MAX_ID = 2**31 - 1


def validate_id(id_value: int) -> None:
    if id_value < 1:
        raise ApiError(code="invalid_id", message="ID must be positive", status=400)
    if id_value > MAX_ID:
        raise ApiError(
            code="id_overflow",
            message=f"ID exceeds maximum value ({MAX_ID})",
            status=400,
        )


def safe_increment_id(current_length: int) -> int:
    if current_length >= MAX_ID:
        raise ApiError(
            code="max_items_reached",
            message=f"Maximum number of items reached ({MAX_ID})",
            status=503,
        )
    return current_length + 1


_DB = {"items": [], "posts": []}

_current_user: Optional[str] = None


@app.post("/items")
def create_item(item: ItemCreate):
    new_id = safe_increment_id(len(_DB["items"]))
    item_data = {"id": new_id, "name": item.name}
    _DB["items"].append(item_data)
    safe_log(
        logging.INFO,
        f"Item created: id={item_data['id']}",
        correlation_id=correlation_id_ctx.get(),
    )
    return item_data


@app.get("/items/{item_id}")
def get_item(item_id: int):
    validate_id(item_id)
    for it in _DB["items"]:
        if it["id"] == item_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


@app.post("/posts", include_in_schema=False)
def create_post(post: PostCreate, request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id or user_id == "anonymous":
        safe_log(
            logging.WARNING,
            "Unauthorized post creation attempt: missing or anonymous user_id",
            correlation_id=correlation_id_ctx.get(),
        )
        raise ApiError(
            code="authentication_required",
            message="Authentication required to create posts",
            status=401,
        )

    new_id = safe_increment_id(len(_DB["posts"]))
    post_data = {
        "id": new_id,
        "title": post.title,
        "body": post.body,
        "status": post.status,
        "tags": post.tags,
        "user_id": user_id,
    }
    _DB["posts"].append(post_data)
    safe_log(
        logging.INFO,
        f"Post created: id={post_data['id']}, status={post.status}, user_id={user_id}",
        correlation_id=correlation_id_ctx.get(),
    )
    return post_data


@app.get("/posts", include_in_schema=False)
def list_posts(
    request: Request, status: Optional[str] = None, tag: Optional[str] = None
):
    user_id = getattr(request.state, "user_id", None) or "anonymous"

    posts = [p for p in _DB["posts"] if p.get("user_id") == user_id]

    if status:
        if status not in ["draft", "published"]:
            raise ApiError(
                code="invalid_status",
                message="status must be 'draft' or 'published'",
                status=400,
            )
        posts = [p for p in posts if p.get("status") == status]

    if tag:
        from app.src.schemas import validate_tag

        try:
            validated_tag = validate_tag(tag)
        except ValueError as e:
            raise ApiError(code="invalid_tag", message=str(e), status=400)
        posts = [p for p in posts if validated_tag in p.get("tags", [])]

    return {"posts": posts, "count": len(posts)}


@app.get("/posts/public")
def get_public_posts(tag: Optional[str] = None):
    posts = [p for p in _DB["posts"] if p.get("status") == "published"]

    if tag:
        from app.src.schemas import validate_tag

        try:
            validated_tag = validate_tag(tag)
        except ValueError as e:
            raise ApiError(code="invalid_tag", message=str(e), status=400)
        posts = [p for p in posts if validated_tag in p.get("tags", [])]

    return {"posts": posts, "count": len(posts)}


@app.get("/posts/{post_id}", include_in_schema=False)
def get_post(post_id: int):
    validate_id(post_id)
    for post in _DB["posts"]:
        if post["id"] == post_id:
            return post
    raise ApiError(code="not_found", message="post not found", status=404)


@app.patch("/posts/{post_id}", include_in_schema=False)
def update_post(post_id: int, post_update: PostUpdate, request: Request):
    validate_id(post_id)
    user_id = getattr(request.state, "user_id", None) or "anonymous"

    post = None
    for p in _DB["posts"]:
        if p["id"] == post_id:
            post = p
            break

    if not post:
        raise ApiError(code="not_found", message="post not found", status=404)

    # Проверка owner-only access (NFR-02, NFR-03, R3)
    if post.get("user_id") != user_id:
        safe_log(
            logging.WARNING,
            f"Unauthorized post update attempt: user_id={user_id}, "
            f"post_id={post_id}, owner={post.get('user_id')}",
            correlation_id=correlation_id_ctx.get(),
        )
        raise ApiError(
            code="forbidden", message="You can only edit your own posts", status=403
        )

    if post_update.title is not None:
        post["title"] = post_update.title
    if post_update.body is not None:
        post["body"] = post_update.body
    if post_update.status is not None:
        post["status"] = post_update.status
    if post_update.tags is not None:
        post["tags"] = post_update.tags

    safe_log(
        logging.INFO,
        f"Post updated: id={post_id}, user_id={user_id}",
        correlation_id=correlation_id_ctx.get(),
    )

    return post


@app.delete("/posts/{post_id}", include_in_schema=False)
def delete_post(post_id: int, request: Request):
    validate_id(post_id)
    user_id = getattr(request.state, "user_id", None) or "anonymous"

    post_index = None
    for i, p in enumerate(_DB["posts"]):
        if p["id"] == post_id:
            post_index = i
            break

    if post_index is None:
        raise ApiError(code="not_found", message="post not found", status=404)

    post = _DB["posts"][post_index]

    if post.get("user_id") != user_id:
        safe_log(
            logging.WARNING,
            f"Unauthorized post delete attempt: user_id={user_id}, "
            f"post_id={post_id}, owner={post.get('user_id')}",
            correlation_id=correlation_id_ctx.get(),
        )
        raise ApiError(
            code="forbidden", message="You can only delete your own posts", status=403
        )

    _DB["posts"].pop(post_index)

    safe_log(
        logging.INFO,
        f"Post deleted: id={post_id}, user_id={user_id}",
        correlation_id=correlation_id_ctx.get(),
    )

    return {"message": "Post deleted successfully", "post_id": post_id}


_USERS_DB = {
    "admin": "password123",
    "user1": "secret456",
    "admin_reset": "password123",
}


@app.post("/register")
async def register(user: UserRegister):
    if user.username in _USERS_DB:
        safe_log(
            logging.WARNING,
            f"Registration attempt for existing user: {user.username}",
            correlation_id=correlation_id_ctx.get(),
        )
        raise ApiError(
            code="user_exists",
            message="User with this username already exists",
            status=409,
        )

    _USERS_DB[user.username] = user.password

    safe_log(
        logging.INFO,
        f"User registered successfully: {user.username}",
        correlation_id=correlation_id_ctx.get(),
    )

    return {
        "message": "User registered successfully",
        "username": user.username,
    }


@app.post("/login")
async def login(request: Request, username: str, password: str):
    client_ip = request.client.host if request.client else "unknown"

    ip_allowed, ip_retry_after = check_ip_rate_limit(client_ip)
    if not ip_allowed:
        safe_log(
            logging.WARNING,
            f"Rate limit exceeded for IP: {client_ip}",
            correlation_id=correlation_id_ctx.get(),
        )
        cid = correlation_id_ctx.get()
        response = problem(
            status=429,
            title="Too Many Requests",
            detail=f"Too many requests. Please try again after {int(ip_retry_after)} seconds.",
            type_="https://example.com/problems/rate-limit-exceeded",
            correlation_id=cid,
            instance=str(request.url.path),
        )
        response.headers["Retry-After"] = str(int(ip_retry_after))
        return response

    account_allowed, account_retry_after = check_account_rate_limit(username)
    if not account_allowed:
        safe_log(
            logging.WARNING,
            f"Rate limit exceeded for account: {username}",
            correlation_id=correlation_id_ctx.get(),
        )
        cid = correlation_id_ctx.get()
        response = problem(
            status=429,
            title="Too Many Requests",
            detail=f"Too many login attempts. Please try again after "
            f"{int(account_retry_after)} seconds.",
            type_="https://example.com/problems/rate-limit-exceeded",
            correlation_id=cid,
            instance=str(request.url.path),
        )
        response.headers["Retry-After"] = str(int(account_retry_after))
        return response

    if username not in _USERS_DB or _USERS_DB[username] != password:
        safe_log(
            logging.WARNING,
            f"Failed login attempt for user: {username}",
            correlation_id=correlation_id_ctx.get(),
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    reset_rate_limit(client_ip)
    reset_rate_limit(username)

    safe_log(
        logging.INFO,
        f"Successful login for user: {username}",
        correlation_id=correlation_id_ctx.get(),
    )

    # Создаем JWT токен с TTL=1 час (ADR-002, NFR-01)
    access_token = create_access_token(data={"sub": username})

    return {
        "message": "Login successful",
        "username": username,
        "access_token": access_token,
        "token_type": "bearer",
    }
