from datetime import datetime, UTC

from core.logger import get_logger

from core.database import RedisInstance, RedisClient


logger = get_logger(__name__)


class RedisSession(RedisInstance):
    def __init__(
        self, redis_client: RedisClient, prefix: str = "session"
    ):
        super().__init__(redis_client, prefix)
        self.redis = redis_client

    async def add_jti_to_blacklist(
        self, jti: str, exp: int
    ) -> bool:
        now = int(datetime.now(tz=UTC).timestamp())
        ttl = exp - now

        if ttl < 0:
            logger.warning(
                f"Token with jti={jti} is already expired."
            )

            return False

        await self.set(
            f"blacklist:jti:{jti}", "Revoked", ttl
        )

        return True

    async def is_jti_in_blacklist(self, jti: str) -> bool:
        return bool(
            await self.redis.exists(self._fmt(f"blacklist:jti:{jti}"))
        )

    