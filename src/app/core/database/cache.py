from typing import Optional, Any
import json

from .redis import RedisClient

from pydantic import BaseModel

from constants import CACHE_EXPIRE_SECONDS


class RedisCache:
    def __init__(self, redis_client: RedisClient, prefix: str = "cache"):
        self.redis = redis_client
        self.prefix = prefix

    def _fmt(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(self._fmt(key))

        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                pass

        return 

    async def set(
        self, key: str, value: Any, ttl: int = CACHE_EXPIRE_SECONDS
    ) -> bool:
        if isinstance(value, BaseModel):
            payload = value.model_dump_json()
        elif isinstance(value, (dict, list)):
            payload = json.dumps(value, default=str)
        else:
            payload = str(value)

        return await self.redis.setex(self._fmt(key), ttl, payload)

    async def delete(self, key: str) -> int:
        return await self.redis.delete(self._fmt(key))