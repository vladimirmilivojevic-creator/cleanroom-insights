from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db import utcnow
from app.deps import DB, CurrentUser
from app.models import Certificate, Organization
from app.schemas import CertificateOut, CertificateVerification

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("")
async def list_certificates(db: DB, user: CurrentUser, trainee_id: int | None = None) -> list[CertificateOut]:
    query = (
        select(Certificate)
        .where(Certificate.organization_id == user.organization_id)
        .order_by(Certificate.issued_at.desc())
    )
    if user.role == "trainee":
        query = query.where(Certificate.trainee_id == user.id)
    elif trainee_id is not None:
        query = query.where(Certificate.trainee_id == trainee_id)
    return [CertificateOut.model_validate(c) for c in await db.scalars(query)]


@router.get("/verify/{code}")
async def verify_certificate(db: DB, code: str) -> CertificateVerification:
    """Public endpoint: anyone holding a certificate code (e.g. an auditor) can check it."""
    certificate = await db.scalar(select(Certificate).where(Certificate.code == code))
    if certificate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    organization = await db.get(Organization, certificate.organization_id)
    return CertificateVerification(
        **CertificateOut.model_validate(certificate).model_dump(),
        organization_name=organization.name if organization else "",
        valid=certificate.valid_until > utcnow(),
    )
