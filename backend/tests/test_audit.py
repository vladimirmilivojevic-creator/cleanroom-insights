import asyncio

import pytest
from sqlalchemy import select

from app.audit import record_audit
from app.db import SessionLocal
from app.models import AuditLog

from .conftest import IS_SQLITE


def test_audit_trail_records_actions(client, admin, trainee):
    sid = client.post("/api/sessions", json={"module": "gowning"}, headers=trainee).json()["id"]
    client.post(f"/api/sessions/{sid}/finish", headers=trainee)

    actions = [e["action"] for e in client.get("/api/audit", headers=admin).json()]
    assert "session.started" in actions
    assert "session.completed" in actions
    assert "user.login" in actions
    assert "user.created" in actions  # from the demo seed


def test_failed_login_is_audited(client, admin):
    client.post("/api/auth/login", data={"username": "lukas@alpine.demo", "password": "wrong"})
    actions = [e["action"] for e in client.get("/api/audit", headers=admin).json()]
    assert "user.login_failed" in actions


def test_audit_is_admin_only(client, trainer):
    assert client.get("/api/audit", headers=trainer).status_code == 403
    assert client.get("/api/audit/verify", headers=trainer).status_code == 403


def test_hash_chain_is_valid(client, admin):
    result = client.get("/api/audit/verify", headers=admin).json()
    assert result["valid"] is True
    assert result["checked"] > 5
    assert result["broken_at_id"] is None


def test_tampering_is_detected(client, admin, db_session):
    async def tamper(db):
        entry = await db.scalar(
            select(AuditLog).where(AuditLog.action == "user.created").order_by(AuditLog.id).limit(1)
        )
        entry.details = {"email": "someone.else@alpine.demo", "role": "admin"}
        await db.commit()
        return entry.id

    tampered_id = db_session(tamper)
    result = client.get("/api/audit/verify", headers=admin).json()
    assert result["valid"] is False
    assert result["broken_at_id"] == tampered_id


@pytest.mark.skipif(IS_SQLITE, reason="row locks need PostgreSQL (CI runs this)")
def test_concurrent_writes_keep_the_chain_valid(client, admin):
    """Regression test: parallel requests used to read the same previous hash and fork the chain."""

    async def write(n: int) -> None:
        async with SessionLocal() as db:
            await record_audit(
                db, organization_id=1, actor_id=None, action="test.concurrent", entity_type="test", entity_id=n
            )
            await asyncio.sleep(0.05)  # keep the transaction open so the writes overlap
            await db.commit()

    async def run() -> None:
        await asyncio.gather(*(write(n) for n in range(5)))

    asyncio.run(run())
    assert client.get("/api/audit/verify", headers=admin).json()["valid"] is True
