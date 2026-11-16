"""Core training-session logic, shared by the REST API and the headset simulator."""

import asyncio
import random
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_audit
from app.config import settings
from app.db import SessionLocal, utcnow
from app.domain import DEVIATIONS, MODULES, SEVERITY_PENALTY, evaluate
from app.live import broadcaster, session_channel
from app.models import Certificate, SessionEvent, TrainingSession, User
from app.schemas import EventIn, EventOut, SessionOut

CERTIFICATE_VALIDITY = timedelta(days=365)


async def get_visible_session(db: AsyncSession, session_id: int, user: User) -> TrainingSession:
    """Load a session the user may see. Other tenants' sessions return 404, not 403,
    so nobody can find out which IDs exist in another organisation."""
    training = await db.get(TrainingSession, session_id)
    if (
        training is None
        or training.organization_id != user.organization_id
        or (user.role == "trainee" and training.trainee_id != user.id)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return training


async def start_session(db: AsyncSession, *, trainee: User, module: str, actor: User) -> TrainingSession:
    training = TrainingSession(
        organization_id=trainee.organization_id,
        trainee_id=trainee.id,
        trainee=trainee,
        module=module,
    )
    db.add(training)
    await db.flush()
    await record_audit(
        db,
        organization_id=trainee.organization_id,
        actor_id=actor.id,
        action="session.started",
        entity_type="training_session",
        entity_id=training.id,
        details={"module": module, "trainee_id": trainee.id},
    )
    await db.commit()
    return training


async def record_event(db: AsyncSession, training: TrainingSession, event_in: EventIn) -> SessionEvent:
    """Validate an event against the module catalogue, store it and push it to live viewers."""
    if training.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Session is already completed")

    module = MODULES[training.module]
    if not module.has_step(event_in.step):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown step '{event_in.step}'")
    if event_in.deviation and event_in.deviation not in module.deviations:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown deviation '{event_in.deviation}'"
        )

    # Severity and penalty come from our catalogue, never from the client.
    severity = DEVIATIONS[event_in.deviation].severity if event_in.deviation else None
    event = SessionEvent(
        session_id=training.id,
        organization_id=training.organization_id,
        kind=event_in.kind,
        step=event_in.step,
        deviation=event_in.deviation,
        severity=severity,
        penalty=SEVERITY_PENALTY[severity] if severity else 0,
    )
    db.add(event)
    await db.commit()

    await broadcaster.publish(
        session_channel(training.id),
        {"type": "event", "event": EventOut.model_validate(event).model_dump(mode="json")},
    )
    return event


async def finish_session(
    db: AsyncSession, training: TrainingSession, actor_id: int | None
) -> Certificate | None:
    """Score the session, add 'skipped_step' deviations, issue a certificate if passed."""
    if training.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Session is already completed")

    module = MODULES[training.module]
    events = list(await db.scalars(select(SessionEvent).where(SessionEvent.session_id == training.id)))
    completed_steps = {e.step for e in events if e.kind == "step"}
    severities = [e.severity for e in events if e.severity]
    result = evaluate(module, completed_steps, severities)

    for step in result.missing_steps:
        db.add(
            SessionEvent(
                session_id=training.id,
                organization_id=training.organization_id,
                kind="deviation",
                step=step,
                deviation="skipped_step",
                severity="critical",
                penalty=SEVERITY_PENALTY["critical"],
            )
        )

    training.status = "completed"
    training.finished_at = utcnow()
    training.score = result.score
    training.passed = result.passed
    await record_audit(
        db,
        organization_id=training.organization_id,
        actor_id=actor_id,
        action="session.completed",
        entity_type="training_session",
        entity_id=training.id,
        details={"score": result.score, "passed": result.passed, "missing_steps": result.missing_steps},
    )

    certificate = None
    if result.passed:
        certificate = Certificate(
            code=uuid4().hex,
            organization_id=training.organization_id,
            trainee_id=training.trainee_id,
            session_id=training.id,
            module=training.module,
            score=result.score,
            valid_until=utcnow() + CERTIFICATE_VALIDITY,
        )
        db.add(certificate)
        await record_audit(
            db,
            organization_id=training.organization_id,
            actor_id=actor_id,
            action="certificate.issued",
            entity_type="certificate",
            entity_id=certificate.code,
            details={"session_id": training.id, "module": training.module},
        )
    await db.commit()

    await broadcaster.publish(
        session_channel(training.id),
        {
            "type": "finished",
            "session": SessionOut.model_validate(training).model_dump(mode="json"),
            "certificate_code": certificate.code if certificate else None,
        },
    )
    return certificate


# --- headset simulator ---------------------------------------------------------------

# Chance per step and per possible deviation for a complete beginner (skill = 0).
DEVIATION_BASE_RATE = {"minor": 0.20, "major": 0.10, "critical": 0.04}
SKIP_BASE_RATE = 0.06


def generate_events(module_code: str, skill: float, rng: random.Random) -> list[EventIn]:
    """Create a realistic event stream: better trainees make fewer mistakes."""
    module = MODULES[module_code]
    mistake_factor = 1 - skill
    events: list[EventIn] = []
    for step in module.steps:
        if rng.random() < SKIP_BASE_RATE * mistake_factor:
            continue  # trainee forgot this step
        for code in module.deviations:
            if rng.random() < DEVIATION_BASE_RATE[DEVIATIONS[code].severity] * mistake_factor:
                events.append(EventIn(kind="deviation", step=step.code, deviation=code))
        events.append(EventIn(kind="step", step=step.code))
    return events


async def run_simulation(session_id: int, skill: float) -> None:
    """Play a simulated VR session in the background, one event at a time."""
    rng = random.Random()
    async with SessionLocal() as db:
        training = await db.get(TrainingSession, session_id)
        if training is None:
            return
        for event in generate_events(training.module, skill, rng):
            await asyncio.sleep(settings.simulator_step_seconds)
            await record_event(db, training, event)
        await finish_session(db, training, actor_id=None)
