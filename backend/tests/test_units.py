"""Unit tests for pure functions and the pub/sub broadcasters."""

import asyncio
import random
from contextlib import aclosing
from datetime import UTC, datetime

import fakeredis
import pytest

from app.config import normalize_database_url
from app.domain import MODULES, evaluate
from app.etl import seconds_until_next_run
from app.live import MemoryBroadcaster, RedisBroadcaster
from app.services import generate_events

GOWNING = MODULES["gowning"]
ALL_STEPS = {s.code for s in GOWNING.steps}


def test_evaluate_perfect_run():
    result = evaluate(GOWNING, ALL_STEPS, [])
    assert (result.score, result.passed, result.missing_steps) == (100, True, [])


def test_evaluate_minor_deviations_can_still_pass():
    result = evaluate(GOWNING, ALL_STEPS, ["minor", "minor", "major"])
    assert result.score == 84
    assert result.passed is True


def test_evaluate_critical_deviation_always_fails():
    result = evaluate(GOWNING, ALL_STEPS, ["critical"])
    assert result.score == 75
    assert result.passed is False


def test_evaluate_score_never_negative():
    assert evaluate(GOWNING, set(), []).score == 0


def test_generate_events_expert_makes_no_mistakes():
    events = generate_events("gowning", skill=1.0, rng=random.Random(1))
    assert [e.step for e in events] == [s.code for s in GOWNING.steps]
    assert all(e.kind == "step" for e in events)


def test_generate_events_beginner_makes_mistakes():
    events = generate_events("gowning", skill=0.0, rng=random.Random(1))
    assert any(e.kind == "deviation" for e in events)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sqlite+aiosqlite:///./x.db", "sqlite+aiosqlite:///./x.db"),
        ("postgres://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("postgresql://u:p@host/db?sslmode=require&channel_binding=require", "postgresql+asyncpg://u:p@host/db?ssl=require"),
        ("postgresql+asyncpg://u:p@host/db?sslmode=disable", "postgresql+asyncpg://u:p@host/db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


def test_seconds_until_next_run():
    assert seconds_until_next_run(datetime(2026, 1, 1, 1, 0, tzinfo=UTC), 2) == 3600
    assert seconds_until_next_run(datetime(2026, 1, 1, 3, 0, tzinfo=UTC), 2) == 23 * 3600


async def _round_trip(broadcaster) -> list[dict]:
    received = []
    async with aclosing(broadcaster.subscribe("session:1")) as messages:
        received.append(await anext(messages))  # "subscribed"
        await broadcaster.publish("session:1", {"type": "event", "n": 1})
        await broadcaster.publish("session:2", {"type": "event", "n": 2})  # other channel
        received.append(await asyncio.wait_for(anext(messages), timeout=2))
    return received


def test_memory_broadcaster():
    received = asyncio.run(_round_trip(MemoryBroadcaster()))
    assert received == [{"type": "subscribed", "channel": "session:1"}, {"type": "event", "n": 1}]


def test_redis_broadcaster():
    async def run():
        return await _round_trip(RedisBroadcaster(fakeredis.FakeAsyncRedis(decode_responses=True)))

    received = asyncio.run(run())
    assert received == [{"type": "subscribed", "channel": "session:1"}, {"type": "event", "n": 1}]
