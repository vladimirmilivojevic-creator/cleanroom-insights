"""FastAPI dependencies: database session, current user and role checks (RBAC)."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DB = Annotated[AsyncSession, Depends(get_db)]


async def user_from_token(db: AsyncSession, token: str) -> User | None:
    """Return the active user behind a JWT, or None. Also used by the WebSocket endpoint."""
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return None
    user = await db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(db: DB, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    user = await user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """Dependency factory: allow only users with one of the given roles."""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is not allowed to do this")
        return user

    return checker


StaffUser = Annotated[User, Depends(require_roles("admin", "trainer"))]
AdminUser = Annotated[User, Depends(require_roles("admin"))]
