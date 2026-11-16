from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.audit import record_audit
from app.deps import DB, CurrentUser
from app.models import User
from app.schemas import MeOut, Token
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(db: DB, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """OAuth2 password flow: send `username` (the email) and `password` as form data."""
    user = await db.scalar(select(User).where(User.email == form.username.lower()))

    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        if user is not None:
            await record_audit(
                db,
                organization_id=user.organization_id,
                actor_id=user.id,
                action="user.login_failed",
                entity_type="user",
                entity_id=user.id,
            )
            await db.commit()
        # Same message for "unknown email" and "wrong password": do not reveal which accounts exist.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    await record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
    return Token(access_token=create_access_token(user.id, user.organization_id, user.role))


@router.get("/me")
async def me(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user)
