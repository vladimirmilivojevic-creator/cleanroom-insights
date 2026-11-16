from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.audit import record_audit
from app.deps import DB, AdminUser, StaffUser
from app.models import User
from app.schemas import Role, UserCreate, UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(db: DB, user: StaffUser, role: Role | None = None) -> list[UserOut]:
    query = select(User).where(User.organization_id == user.organization_id).order_by(User.full_name)
    if role:
        query = query.where(User.role == role)
    return [UserOut.model_validate(u) for u in await db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(db: DB, admin: AdminUser, body: UserCreate) -> UserOut:
    email = body.email.lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    new_user = User(
        organization_id=admin.organization_id,
        email=email,
        full_name=body.full_name,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(new_user)
    await db.flush()
    await record_audit(
        db,
        organization_id=admin.organization_id,
        actor_id=admin.id,
        action="user.created",
        entity_type="user",
        entity_id=new_user.id,
        details={"email": email, "role": body.role},
    )
    await db.commit()
    return UserOut.model_validate(new_user)


@router.patch("/{user_id}")
async def update_user(db: DB, admin: AdminUser, user_id: int, body: UserUpdate) -> UserOut:
    target = await db.get(User, user_id)
    if target is None or target.organization_id != admin.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own account")

    changes = body.model_dump(exclude_unset=True)
    # GMP audit trail: keep the old and the new value of every changed field.
    diff = {field: {"old": getattr(target, field), "new": value} for field, value in changes.items()}
    for field, value in changes.items():
        setattr(target, field, value)

    await record_audit(
        db,
        organization_id=admin.organization_id,
        actor_id=admin.id,
        action="user.updated",
        entity_type="user",
        entity_id=target.id,
        details=diff,
    )
    await db.commit()
    return UserOut.model_validate(target)
