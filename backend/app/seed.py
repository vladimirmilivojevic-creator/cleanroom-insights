"""Demo data: two organisations with users and eight weeks of training history.

Run with ``python -m app.seed``. It does nothing if data already exists.
All demo accounts use the password ``demo1234``.
"""

import asyncio
import random
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.db import SessionLocal, utcnow
from app.domain import DEVIATIONS, MODULES, SEVERITY_PENALTY, evaluate
from app.models import Certificate, Organization, SessionEvent, TrainingSession, User
from app.security import hash_password
from app.services import CERTIFICATE_VALIDITY, generate_events

DEMO_PASSWORD = "demo1234"

DEMO_ORGANIZATIONS = [
    {
        "name": "Alpine Pharma GmbH",
        "domain": "alpine.demo",
        "admin": "Markus Eder",
        "trainer": "Katharina Hofer",
        "trainees": [
            "Lukas Gruber", "Sophie Wagner", "Jonas Bauer", "Lena Pichler", "Maximilian Steiner", "Hannah Moser",
        ],
    },
    {
        "name": "Nordic Biologics AB",
        "domain": "nordic.demo",
        "admin": "Ingrid Dahl",
        "trainer": "Erik Lindqvist",
        "trainees": ["Astrid Nilsson", "Oskar Berg", "Freja Holm"],
    },
]


async def _add_user(db: AsyncSession, org: Organization, email: str, name: str, role: str, password_hash: str) -> User:
    user = User(organization_id=org.id, email=email, full_name=name, role=role, password_hash=password_hash)
    db.add(user)
    await db.flush()
    await record_audit(
        db, organization_id=org.id, actor_id=None, action="user.created",
        entity_type="user", entity_id=user.id, details={"email": email, "role": role},
    )
    return user


async def _add_history(db: AsyncSession, trainee: User, rng: random.Random) -> None:
    """Past sessions for one trainee; skill grows with practice."""
    skill = rng.uniform(0.25, 0.55)
    now = utcnow()
    session_count = rng.randint(5, 9)
    for i in range(session_count):
        module_code = "gowning" if i % 2 == 0 else "aseptic_intervention"
        module = MODULES[module_code]
        day = now - timedelta(days=round(56 - i * (50 / session_count)))
        started = day.replace(hour=rng.randint(7, 15), minute=rng.choice((0, 15, 30, 45)), second=0, microsecond=0)
        events = generate_events(module_code, min(skill, 0.98), rng)

        completed = {e.step for e in events if e.kind == "step"}
        severities = [DEVIATIONS[e.deviation].severity for e in events if e.deviation]
        result = evaluate(module, completed, severities)

        training = TrainingSession(
            organization_id=trainee.organization_id, trainee_id=trainee.id, module=module_code,
            status="completed", started_at=started,
            finished_at=started + timedelta(seconds=20 * (len(events) + 1)),
            score=result.score, passed=result.passed,
        )
        db.add(training)
        await db.flush()

        all_events = [(e.kind, e.step, e.deviation) for e in events]
        all_events += [("deviation", step, "skipped_step") for step in result.missing_steps]
        for n, (kind, step, deviation) in enumerate(all_events):
            severity = DEVIATIONS[deviation].severity if deviation else None
            db.add(SessionEvent(
                session_id=training.id, organization_id=trainee.organization_id, kind=kind, step=step,
                deviation=deviation, severity=severity,
                penalty=SEVERITY_PENALTY[severity] if severity else 0,
                created_at=started + timedelta(seconds=20 * (n + 1)),
            ))

        if result.passed:
            db.add(Certificate(
                code=uuid4().hex, organization_id=trainee.organization_id, trainee_id=trainee.id,
                session_id=training.id, module=module_code, score=result.score,
                issued_at=training.finished_at, valid_until=training.finished_at + CERTIFICATE_VALIDITY,
            ))
        skill += rng.uniform(0.04, 0.10)


async def seed_demo(db: AsyncSession) -> bool:
    """Create demo data if the database is empty. Returns True if data was created."""
    if await db.scalar(select(func.count(Organization.id))):
        return False

    rng = random.Random(2026)  # fixed seed: same demo data every time
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once, reused for all demo users
    for spec in DEMO_ORGANIZATIONS:
        org = Organization(name=spec["name"])
        db.add(org)
        await db.flush()
        domain = spec["domain"]
        await _add_user(db, org, f"admin@{domain}", spec["admin"], "admin", password_hash)
        await _add_user(db, org, f"trainer@{domain}", spec["trainer"], "trainer", password_hash)
        for name in spec["trainees"]:
            email = f"{name.split()[0].lower()}@{domain}"
            trainee = await _add_user(db, org, email, name, "trainee", password_hash)
            await _add_history(db, trainee, rng)
    await db.commit()
    return True


async def main() -> None:
    async with SessionLocal() as db:
        created = await seed_demo(db)
    print("Demo data created." if created else "Database already has data, nothing to do.")


if __name__ == "__main__":
    asyncio.run(main())
