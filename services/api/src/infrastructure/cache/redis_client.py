import json
from typing import Any, Optional
import redis.asyncio as redis
from src.core.config import settings
from src.core.logging import logger

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)


class CacheService:
    def __init__(self, client: redis.Redis):
        self.client = client

    async def get_json(self, key: str) -> Optional[Any]:
        try:
            val = await self.client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning(f"Redis get_json failure on key {key}: {e}")
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        try:
            await self.client.set(key, json.dumps(value), ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning(f"Redis set_json failure on key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failure on key {key}: {e}")
            return False

    async def publish_event(self, channel: str, event_data: dict) -> None:
        try:
            await self.client.publish(channel, json.dumps(event_data))
        except Exception as e:
            logger.warning(f"Redis publish failure on channel {channel}: {e}")
