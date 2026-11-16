"""Publish/subscribe for live sessions.

With ``REDIS_URL`` set, messages go through Redis pub/sub, so several API instances
can share live updates. Without Redis (local dev, tests) an in-process broadcaster
with asyncio queues does the same job for a single instance.

Both implementations first yield a ``{"type": "subscribed"}`` message once the
subscription is active, so a client knows it will not miss anything from then on.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from app.config import settings

Message = dict[str, Any]


def session_channel(session_id: int) -> str:
    return f"session:{session_id}"


class MemoryBroadcaster:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[Message]]] = defaultdict(set)

    async def publish(self, channel: str, message: Message) -> None:
        for queue in list(self._queues[channel]):
            queue.put_nowait(message)

    async def subscribe(self, channel: str) -> AsyncIterator[Message]:
        queue: asyncio.Queue[Message] = asyncio.Queue()
        self._queues[channel].add(queue)
        try:
            yield {"type": "subscribed", "channel": channel}
            while True:
                yield await queue.get()
        finally:
            self._queues[channel].discard(queue)


class RedisBroadcaster:
    def __init__(self, client: redis.Redis) -> None:
        self._redis = client

    async def publish(self, channel: str, message: Message) -> None:
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncIterator[Message]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield {"type": "subscribed", "channel": channel}
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    yield json.loads(raw["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


def create_broadcaster() -> MemoryBroadcaster | RedisBroadcaster:
    if settings.redis_url:
        return RedisBroadcaster(redis.from_url(settings.redis_url, decode_responses=True))
    return MemoryBroadcaster()


broadcaster = create_broadcaster()
