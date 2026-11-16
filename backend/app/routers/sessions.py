import random
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select

from app.deps import DB, CurrentUser, StaffUser
from app.domain import DEVIATIONS, MODULES
from app.models import Certificate, SessionEvent, TrainingSession, User
from app.schemas import (
    DeviationOut,
    EventIn,
    EventOut,
    ModuleOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
    SimulationCreate,
    StepOut,
)
from app.services import (
    finish_session,
    get_visible_session,
    record_event,
    run_simulation,
    start_session,
)

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/modules")
async def list_modules(user: CurrentUser) -> list[ModuleOut]:
    return [
        ModuleOut(
            code=m.code,
            title=m.title,
            description=m.description,
            steps=[StepOut(code=s.code, title=s.title) for s in m.steps],
            deviations=[DeviationOut(**DEVIATIONS[d].__dict__) for d in m.deviations],
        )
        for m in MODULES.values()
    ]


async def _get_trainee(db: DB, trainee_id: int, organization_id: int) -> User:
    trainee = await db.get(User, trainee_id)
    if trainee is None or trainee.organization_id != organization_id or trainee.role != "trainee":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trainee not found")
    return trainee


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(db: DB, user: CurrentUser, body: SessionCreate) -> SessionOut:
    """Called when a trainee puts on the headset and starts a module."""
    if user.role == "trainee":
        trainee = user
    elif body.trainee_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "trainee_id is required")
    else:
        trainee = await _get_trainee(db, body.trainee_id, user.organization_id)

    training = await start_session(db, trainee=trainee, module=body.module, actor=user)
    return SessionOut.model_validate(training)


@router.post("/sessions/simulate", status_code=status.HTTP_201_CREATED)
async def simulate_session(
    db: DB, user: StaffUser, body: SimulationCreate, background: BackgroundTasks
) -> SessionOut:
    """Start a session and let a simulated headset send events in the background."""
    trainee = await _get_trainee(db, body.trainee_id, user.organization_id)
    training = await start_session(db, trainee=trainee, module=body.module, actor=user)
    skill = body.skill if body.skill is not None else random.uniform(0.3, 0.95)
    background.add_task(run_simulation, training.id, skill)
    return SessionOut.model_validate(training)


@router.get("/sessions")
async def list_sessions(
    db: DB,
    user: CurrentUser,
    session_status: Annotated[str | None, Query(alias="status")] = None,
    trainee_id: int | None = None,
    limit: int = 50,
) -> list[SessionOut]:
    query = (
        select(TrainingSession)
        .where(TrainingSession.organization_id == user.organization_id)
        .order_by(TrainingSession.started_at.desc())
        .limit(min(limit, 200))
    )
    if user.role == "trainee":  # trainees only ever see their own sessions
        query = query.where(TrainingSession.trainee_id == user.id)
    elif trainee_id is not None:
        query = query.where(TrainingSession.trainee_id == trainee_id)
    if session_status:
        query = query.where(TrainingSession.status == session_status)
    return [SessionOut.model_validate(s) for s in await db.scalars(query)]


@router.get("/sessions/{session_id}")
async def get_session(db: DB, user: CurrentUser, session_id: int) -> SessionDetail:
    training = await get_visible_session(db, session_id, user)
    events = await db.scalars(
        select(SessionEvent).where(SessionEvent.session_id == training.id).order_by(SessionEvent.id)
    )
    certificate_code = await db.scalar(
        select(Certificate.code).where(Certificate.session_id == training.id)
    )
    detail = SessionDetail.model_validate(training)
    detail.events = [EventOut.model_validate(e) for e in events]
    detail.certificate_code = certificate_code
    return detail


@router.post("/sessions/{session_id}/events", status_code=status.HTTP_201_CREATED)
async def ingest_event(db: DB, user: CurrentUser, session_id: int, body: EventIn) -> EventOut:
    """Ingest one event from the VR headset."""
    training = await get_visible_session(db, session_id, user)
    event = await record_event(db, training, body)
    return EventOut.model_validate(event)


@router.post("/sessions/{session_id}/finish")
async def finish(db: DB, user: CurrentUser, session_id: int) -> SessionDetail:
    training = await get_visible_session(db, session_id, user)
    await finish_session(db, training, actor_id=user.id)
    return await get_session(db, user, session_id)
