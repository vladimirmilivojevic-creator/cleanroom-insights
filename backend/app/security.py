"""Password hashing (bcrypt) and JWT access tokens."""

from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.config import settings
from app.db import utcnow

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int, organization_id: int, role: str) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "org": organization_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises ``jwt.PyJWTError`` if the token is invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
