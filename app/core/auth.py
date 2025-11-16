import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import PyJWTError

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "your-256-bit-secret-key-here-change-in-production-32-chars-minimum",
)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "iat": datetime.now(timezone.utc),
            "exp": expire,
            "iss": "simple-blog",
            "aud": "simple-blog-users",
        }
    )

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience="simple-blog-users",
            issuer="simple-blog",
        )

        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            return None

        return payload

    except (PyJWTError, ValueError):
        return None


def get_current_user(token: str) -> Optional[str]:
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None
