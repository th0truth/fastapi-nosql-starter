from typing import Optional

import redis.asyncio as aioredis

from core.config import settings
from core.logger import get_logger

from core.database import DBConnection


logger = get_logger(__name__)


class RedisClient(DBConnection):
    _instance: Optional["RedisClient"] = None
    _client: Optional[aioredis.Redis] = None

    @classmethod
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    @classmethod
    async def connect(cls):
        """Establish Redis connection."""
        try:
            cls._client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USERNAME,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                db=settings.REDIS_DB,
            )
            alive = await cls._client.ping()

            if not alive:
                logger.error(
                    "Couldn't connect to Redis: "
                    f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                )

                return
            
            logger.info("[+] Successfully connected to Redis.")

            return cls._instance
        except aioredis.ConnectionError as e:
            logger.error("Error connecting to Redis: %s", e)

            return

    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if not cls._client:
            try:
                await cls._client.aclose()
                logger.info("[+] Redis connection closed.")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}", exc_info=True)
            finally:
                cls._client = None

    def __getattr__(self, name) -> aioredis.Redis:
        """Delegate attribute access to the underlying Redis client."""
        if not self._client:
            raise RuntimeError(
                "Redis client not connected."
            )

        return getattr(self._client, name)
