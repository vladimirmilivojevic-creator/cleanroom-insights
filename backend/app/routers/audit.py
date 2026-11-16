from fastapi import APIRouter
from sqlalchemy import select

from app.audit import verify_chain
from app.deps import DB, AdminUser
from app.models import AuditLog
from app.schemas import AuditOut, AuditVerification

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit(db: DB, admin: AdminUser, limit: int = 100) -> list[AuditOut]:
    entries = await db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == admin.organization_id)
        .order_by(AuditLog.id.desc())
        .limit(min(limit, 500))
    )
    return [AuditOut.model_validate(e) for e in entries]


@router.get("/verify")
async def verify_audit_chain(db: DB, admin: AdminUser) -> AuditVerification:
    valid, checked, broken_at = await verify_chain(db, admin.organization_id)
    return AuditVerification(valid=valid, checked=checked, broken_at_id=broken_at)
