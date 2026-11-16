from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, select

from app.db import utcnow
from app.deps import DB, AdminUser, CurrentUser, StaffUser
from app.domain import DEVIATIONS, MODULES
from app.etl import run_etl, warehouse_report
from app.models import Certificate, SessionEvent, TrainingSession, User
from app.schemas import (
    CertificateOut,
    DeviationOut,
    Heatmap,
    HeatmapCell,
    Overview,
    SessionOut,
    StepOut,
    TraineeDetail,
    TraineeProgress,
    UserOut,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

PASSED_AS_NUMBER = case((TrainingSession.passed.is_(True), 100.0), else_=0.0)


@router.get("/overview")
async def overview(db: DB, user: StaffUser) -> Overview:
    org = user.organization_id
    trainees = await db.scalar(
        select(func.count(User.id)).where(User.organization_id == org, User.role == "trainee")
    )
    completed, pass_rate, average_score = (await db.execute(
        select(func.count(TrainingSession.id), func.avg(PASSED_AS_NUMBER), func.avg(TrainingSession.score))
        .where(TrainingSession.organization_id == org, TrainingSession.status == "completed")
    )).one()
    running = await db.scalar(
        select(func.count(TrainingSession.id))
        .where(TrainingSession.organization_id == org, TrainingSession.status == "running")
    )
    valid_certificates = await db.scalar(
        select(func.count(Certificate.id))
        .where(Certificate.organization_id == org, Certificate.valid_until > utcnow())
    )
    return Overview(
        trainees=trainees or 0,
        completed_sessions=completed or 0,
        running_sessions=running or 0,
        pass_rate=round(float(pass_rate or 0), 1),
        average_score=round(float(average_score or 0), 1),
        valid_certificates=valid_certificates or 0,
    )


@router.get("/heatmap")
async def deviation_heatmap(db: DB, user: StaffUser, module: str = "gowning") -> Heatmap:
    """How often each deviation happens at each step of a module."""
    if module not in MODULES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown module")
    rows = await db.execute(
        select(SessionEvent.step, SessionEvent.deviation, func.count(SessionEvent.id))
        .join(TrainingSession, TrainingSession.id == SessionEvent.session_id)
        .where(
            SessionEvent.organization_id == user.organization_id,
            SessionEvent.kind == "deviation",
            TrainingSession.module == module,
        )
        .group_by(SessionEvent.step, SessionEvent.deviation)
    )
    m = MODULES[module]
    return Heatmap(
        module=module,
        steps=[StepOut(code=s.code, title=s.title) for s in m.steps],
        deviations=[DeviationOut(**DEVIATIONS[d].__dict__) for d in (*m.deviations, "skipped_step")],
        cells=[HeatmapCell(step=step, deviation=dev, count=count) for step, dev, count in rows],
    )


@router.get("/trainees")
async def trainee_progress(db: DB, user: StaffUser) -> list[TraineeProgress]:
    org = user.organization_id
    trainees = await db.scalars(
        select(User).where(User.organization_id == org, User.role == "trainee").order_by(User.full_name)
    )
    stats = {
        trainee_id: (count, avg, passed)
        for trainee_id, count, avg, passed in await db.execute(
            select(
                TrainingSession.trainee_id,
                func.count(TrainingSession.id),
                func.avg(TrainingSession.score),
                func.sum(case((TrainingSession.passed.is_(True), 1), else_=0)),
            )
            .where(TrainingSession.organization_id == org, TrainingSession.status == "completed")
            .group_by(TrainingSession.trainee_id)
        )
    }
    last_scores: dict[int, int] = {}
    for trainee_id, score in await db.execute(
        select(TrainingSession.trainee_id, TrainingSession.score)
        .where(TrainingSession.organization_id == org, TrainingSession.status == "completed")
        .order_by(TrainingSession.finished_at)
    ):
        last_scores[trainee_id] = score  # ordered by time, so the last one wins
    certified: dict[int, set[str]] = {}
    for trainee_id, module in await db.execute(
        select(Certificate.trainee_id, Certificate.module)
        .where(Certificate.organization_id == org, Certificate.valid_until > utcnow())
    ):
        certified.setdefault(trainee_id, set()).add(module)

    result = []
    for t in trainees:
        count, avg, passed = stats.get(t.id, (0, None, 0))
        result.append(TraineeProgress(
            trainee_id=t.id,
            trainee_name=t.full_name,
            sessions=count,
            average_score=round(float(avg), 1) if avg is not None else None,
            last_score=last_scores.get(t.id),
            passed_sessions=passed or 0,
            certified_modules=sorted(certified.get(t.id, set())),
        ))
    return result


@router.get("/trainees/{trainee_id}")
async def trainee_detail(db: DB, user: CurrentUser, trainee_id: int) -> TraineeDetail:
    if user.role == "trainee" and user.id != trainee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trainee not found")
    trainee = await db.get(User, trainee_id)
    if trainee is None or trainee.organization_id != user.organization_id or trainee.role != "trainee":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trainee not found")

    sessions = await db.scalars(
        select(TrainingSession).where(TrainingSession.trainee_id == trainee_id).order_by(TrainingSession.started_at)
    )
    certificates = await db.scalars(
        select(Certificate).where(Certificate.trainee_id == trainee_id).order_by(Certificate.issued_at.desc())
    )
    return TraineeDetail(
        trainee=UserOut.model_validate(trainee),
        sessions=[SessionOut.model_validate(s) for s in sessions],
        certificates=[CertificateOut.model_validate(c) for c in certificates],
    )


@router.get("/warehouse")
async def warehouse(user: StaffUser) -> dict[str, Any]:
    """Reports computed by DuckDB on the Parquet files of the last ETL run."""
    return warehouse_report(user.organization_id)


@router.post("/etl")
async def run_etl_now(db: DB, admin: AdminUser) -> dict[str, Any]:
    """Run the nightly export right now (admins only)."""
    return await run_etl(db)
