"""Nightly ETL: PostgreSQL -> Parquet files, analysed with DuckDB.

Extract:   read sessions and events with SQLAlchemy (operational database).
Transform: flatten into two analytics tables (one row per session / per event).
Load:      write Parquet files; DuckDB queries them directly for the reports.

The operational database stays fast for the app, and heavy analytics run on
columnar files. The same files could be registered in a DuckLake catalog or
pushed to S3 without changing the reports.
"""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionLocal, utcnow
from app.models import SessionEvent, TrainingSession

logger = logging.getLogger(__name__)

SESSIONS_DDL = """
CREATE TABLE sessions (
    id INTEGER, organization_id INTEGER, trainee_id INTEGER, module VARCHAR,
    status VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP, score INTEGER, passed BOOLEAN
)"""
EVENTS_DDL = """
CREATE TABLE events (
    id INTEGER, session_id INTEGER, organization_id INTEGER, kind VARCHAR, step VARCHAR,
    deviation VARCHAR, severity VARCHAR, penalty INTEGER, created_at TIMESTAMP
)"""


def _naive_utc(value: datetime | None) -> datetime | None:
    """Parquet gets plain UTC timestamps."""
    return value.astimezone(UTC).replace(tzinfo=None) if value else None


def warehouse_path() -> Path:
    return Path(settings.warehouse_dir)


async def run_etl(db: AsyncSession) -> dict[str, Any]:
    # Extract
    sessions = (await db.execute(select(
        TrainingSession.id, TrainingSession.organization_id, TrainingSession.trainee_id,
        TrainingSession.module, TrainingSession.status, TrainingSession.started_at,
        TrainingSession.finished_at, TrainingSession.score, TrainingSession.passed,
    ))).all()
    events = (await db.execute(select(
        SessionEvent.id, SessionEvent.session_id, SessionEvent.organization_id, SessionEvent.kind,
        SessionEvent.step, SessionEvent.deviation, SessionEvent.severity, SessionEvent.penalty,
        SessionEvent.created_at,
    ))).all()

    # Transform
    session_rows = [(*r[:5], _naive_utc(r[5]), _naive_utc(r[6]), r[7], r[8]) for r in sessions]
    event_rows = [(*r[:8], _naive_utc(r[8])) for r in events]

    # Load: write to a temp file first, then rename, so readers never see half a file.
    out = warehouse_path()
    out.mkdir(parents=True, exist_ok=True)
    with duckdb.connect() as con:
        con.execute(SESSIONS_DDL)
        con.execute(EVENTS_DDL)
        if session_rows:
            con.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", session_rows)
        if event_rows:
            con.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", event_rows)
        for table in ("sessions", "events"):
            tmp = out / f"{table}.parquet.tmp"
            con.execute(f"COPY {table} TO '{tmp.as_posix()}' (FORMAT parquet)")
            os.replace(tmp, out / f"{table}.parquet")

    summary = {
        "finished_at": utcnow().isoformat(),
        "sessions": len(session_rows),
        "events": len(event_rows),
    }
    (out / "last_run.json").write_text(json.dumps(summary))
    logger.info("ETL finished: %s", summary)
    return summary


def warehouse_report(organization_id: int) -> dict[str, Any]:
    """Analytics queries that DuckDB runs straight on the Parquet files."""
    out = warehouse_path()
    sessions_file = out / "sessions.parquet"
    events_file = out / "events.parquet"
    if not sessions_file.exists():
        return {"last_run": None, "weekly": [], "modules": [], "top_deviations": []}

    sessions = f"read_parquet('{sessions_file.as_posix()}')"
    events = f"read_parquet('{events_file.as_posix()}')"
    with duckdb.connect() as con:
        weekly = con.execute(f"""
            SELECT strftime(date_trunc('week', started_at), '%Y-%m-%d') AS week,
                   count(*) AS sessions,
                   round(avg(score), 1) AS average_score,
                   round(100 * avg(CASE WHEN passed THEN 1 ELSE 0 END), 1) AS pass_rate
            FROM {sessions}
            WHERE organization_id = ? AND status = 'completed'
            GROUP BY 1 ORDER BY 1
        """, [organization_id]).fetchall()

        modules = con.execute(f"""
            SELECT module, count(*) AS sessions, round(avg(score), 1) AS average_score,
                   round(100 * avg(CASE WHEN passed THEN 1 ELSE 0 END), 1) AS pass_rate
            FROM {sessions}
            WHERE organization_id = ? AND status = 'completed'
            GROUP BY 1 ORDER BY 1
        """, [organization_id]).fetchall()

        top_deviations = con.execute(f"""
            SELECT deviation, severity, count(*) AS occurrences, sum(penalty) AS total_penalty
            FROM {events}
            WHERE organization_id = ? AND kind = 'deviation'
            GROUP BY 1, 2 ORDER BY total_penalty DESC LIMIT 5
        """, [organization_id]).fetchall()

    last_run_file = out / "last_run.json"
    return {
        "last_run": json.loads(last_run_file.read_text()) if last_run_file.exists() else None,
        "weekly": [dict(zip(("week", "sessions", "average_score", "pass_rate"), r, strict=True)) for r in weekly],
        "modules": [dict(zip(("module", "sessions", "average_score", "pass_rate"), r, strict=True)) for r in modules],
        "top_deviations": [
            dict(zip(("deviation", "severity", "occurrences", "total_penalty"), r, strict=True))
            for r in top_deviations
        ],
    }


def seconds_until_next_run(now: datetime, hour_utc: int) -> float:
    next_run = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


async def nightly_etl_loop() -> None:
    """Runs inside the API process. With several instances you would use a cron job instead."""
    while True:
        await asyncio.sleep(seconds_until_next_run(utcnow(), settings.etl_hour_utc))
        try:
            async with SessionLocal() as db:
                await run_etl(db)
        except Exception:
            logger.exception("Nightly ETL failed")
