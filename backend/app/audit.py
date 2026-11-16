"""GMP-style audit trail: append-only and hash-chained per organisation.

There is no endpoint that updates or deletes audit entries. Each entry's hash covers
its own content plus the previous entry's hash, so any later change to an old row
breaks the chain and ``verify_chain`` reports where.
"""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import utcnow
from app.models import AuditLog, Organization

GENESIS_HASH = "0" * 64


def compute_hash(entry: AuditLog) -> str:
    payload = {
        "organization_id": entry.organization_id,
        "actor_id": entry.actor_id,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(timespec="seconds"),
        "prev_hash": entry.prev_hash,
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


async def record_audit(
    db: AsyncSession,
    *,
    organization_id: int,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit entry to the current transaction (the caller commits).

    Two requests of the same tenant writing at the same moment would both read the
    same "previous" entry and fork the chain. So we first lock the organisation row
    (SELECT ... FOR UPDATE): the second transaction waits until the first commits.
    PostgreSQL only; SQLite (local development) has no row locks.
    """
    await db.execute(
        select(Organization.id).where(Organization.id == organization_id).with_for_update()
    )
    previous = await db.scalar(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    entry = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        created_at=utcnow(),
        prev_hash=previous.hash if previous else GENESIS_HASH,
    )
    entry.hash = compute_hash(entry)
    db.add(entry)
    await db.flush()  # so the next audit call in the same transaction sees this entry
    return entry


async def verify_chain(db: AsyncSession, organization_id: int) -> tuple[bool, int, int | None]:
    """Walk the chain from the oldest entry. Returns (valid, checked, broken_at_id)."""
    entries = await db.scalars(
        select(AuditLog).where(AuditLog.organization_id == organization_id).order_by(AuditLog.id)
    )
    expected_prev = GENESIS_HASH
    checked = 0
    for entry in entries:
        if entry.prev_hash != expected_prev or entry.hash != compute_hash(entry):
            return False, checked, entry.id
        expected_prev = entry.hash
        checked += 1
    return True, checked, None
