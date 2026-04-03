"""
Cache client wrapper (Redis/Dragonfly).
"""

import redis.asyncio as redis
from config import settings
import logging
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)

class CacheClient:
    def __init__(self, url: str):
        self._url = url
        self._client = None

    async def connect(self):
        if not self._client:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
            )
        await self._client.ping()

    async def disconnect(self):
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Any:
        return await self._client.get(key)

    async def set(self, key: str, value: str, expire: int = None) -> bool:
        return await self._client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        return await self._client.delete(key)
    
    async def ping(self):
        return await self._client.ping()

    def pipeline(self):
        """Return a pipeline object for bulk operations."""
        return self._client.pipeline()

    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        """Pub/Sub subscriber generator."""
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield message

    async def publish(self, channel: str, message: str) -> int:
        """Pub/Sub publisher."""
        return await self._client.publish(channel, message)

cache = CacheClient(settings.CACHE_URL)
