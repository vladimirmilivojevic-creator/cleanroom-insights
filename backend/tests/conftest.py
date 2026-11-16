"""Test setup.

Tests use SQLite by default (no services needed). CI runs the same tests against
PostgreSQL by setting DATABASE_URL. Every test starts with an empty database that
gets the demo data, so tests are independent of each other.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

# Settings are read at import time, so configure the environment first.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ["DB_POOL"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["SIMULATOR_STEP_SECONDS"] = "0"
os.environ["ETL_ENABLED"] = "false"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"  # the fixtures below seed the database
os.environ["WAREHOUSE_DIR"] = tempfile.mkdtemp(prefix="warehouse-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_demo  # noqa: E402

PASSWORD = "demo1234"


IS_SQLITE = os.environ["DATABASE_URL"].startswith("sqlite")
SQLITE_FILE = Path("test.db")
SQLITE_TEMPLATE = Path("test-template.db")


async def _reset_and_seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_demo(db)


@pytest.fixture(scope="session")
def seeded_template():
    """With SQLite we seed once and copy the file for every test (much faster)."""
    if IS_SQLITE:
        asyncio.run(_reset_and_seed())
        shutil.copy(SQLITE_FILE, SQLITE_TEMPLATE)
        yield
        SQLITE_TEMPLATE.unlink(missing_ok=True)
    else:
        yield


@pytest.fixture
def client(seeded_template):
    if IS_SQLITE:
        shutil.copy(SQLITE_TEMPLATE, SQLITE_FILE)
    else:
        asyncio.run(_reset_and_seed())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """For tests that need to look at the database directly."""

    def run(coro_factory):
        async def runner():
            async with SessionLocal() as db:
                return await coro_factory(db)

        return asyncio.run(runner())

    return run


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client, "admin@alpine.demo")


@pytest.fixture
def trainer(client):
    return login(client, "trainer@alpine.demo")


@pytest.fixture
def trainee(client):
    return login(client, "lukas@alpine.demo")


@pytest.fixture
def other_org_trainer(client):
    return login(client, "trainer@nordic.demo")
