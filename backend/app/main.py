"""CleanroomInsights API: analytics for VR cleanroom training sessions."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.etl import nightly_etl_loop, run_etl
from app.routers import analytics, audit, auth, certificates, live, sessions, users
from app.seed import seed_demo

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    if settings.seed_demo_data:
        async with SessionLocal() as db:
            await seed_demo(db)

    etl_task = None
    if settings.etl_enabled:
        async with SessionLocal() as db:
            await run_etl(db)  # fresh analytics right after start, then every night
        etl_task = asyncio.create_task(nightly_etl_loop())

    yield

    if etl_task:
        etl_task.cancel()


app = FastAPI(
    title="CleanroomInsights API",
    version="1.0.0",
    description="Ingests VR cleanroom training events, streams live sessions and serves training analytics.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, users.router, sessions.router, live.router, analytics.router,
               certificates.router, audit.router):
    app.include_router(router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
