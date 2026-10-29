from typing import Optional, Any
import json
import time

from core.database import RedisInstance, RedisClient


class RedisCache(RedisInstance):
    def __init__(
        self, redis_client: RedisClient, prefix: str = "cache"
    ):
        super().__init__(redis_client, prefix)
        self.open_until = 0
        self.failures = 0
        self.max_failures = 3

    async def get(self, key: str) -> Optional[Any]:
        if time.time() < self.open_until:
            return

        try:
            data = await self.redis.get(self._fmt(key))

            if data:
                return json.loads(data)

        except Exception:
            self.failures += 1

            if self.failures >= self.max_failures:
                self.open_until = time.time() + 60

        return 
