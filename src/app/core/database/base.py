from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
import json

from pydantic import BaseModel

if TYPE_CHECKING:
    from .redis import RedisClient

from constants import CACHE_EXPIRE_SECONDS


class DBConnection(ABC):
    """Abstract base class for DB instance client."""

    @classmethod
    @abstractmethod
    async def connect(cls):
        """Establish instance connection."""

    @classmethod
    @abstractmethod
    async def close(cls):
        """Close instance connection."""


class RedisInstance(ABC):
    def __init__(self, redis_client: RedisClient, prefix: str):
        self.redis = redis_client
        self.prefix = prefix

    def _fmt(self, key: str) -> str:
        return f"{self.prefix}:{key}"

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