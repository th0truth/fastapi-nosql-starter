from typing import Optional, Any
import json

from .redis import RedisClient


class RedisCache:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self._cache_key = "cache:{key}"

    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis_client.get(
            self._cache_key.format(key=key)
        )

        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                pass

        return 
