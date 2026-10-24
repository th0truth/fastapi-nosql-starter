from datetime import UTC, datetime, timedelta
import uuid
import jwt

from core.config import settings
from core.logger import get_logger

from core.database import RedisClient


logger = get_logger(__name__)


class OAuthJWTBearer:
    """
    JSON Web Token (JWT) is a compact, URL-safe means of representing
    claims to be transferred between two parties.
    """

    @staticmethod
    def encode(payload: dict) -> dict:
        """Encodes a given payload into a JWT."""
        jti = str(uuid.uuid4().hex)

        now = datetime.now(tz=UTC)
        exp = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

        payload.update({"jti": jti, "exp": exp, "iat": now})

        return {
            "jwt": jwt.encode(
                payload=payload,
                key=settings.PRIVATE_KEY_PEM,
                algorithm=settings.JWT_ALGORITHM,
            ),
            "jti": jti,
        }

    @staticmethod
    def decode(token: str) -> dict | None:
        """Decodes a JWT, returning the payload."""
        try:
            return jwt.decode(
                jwt=token,
                key=settings.PUBLIC_KEY_PEM,
                algorithms=settings.JWT_ALGORITHM,
            )
        except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
            logger.exception("Unable to decode JWT: %s", e)

            return

    @staticmethod
    async def refresh(payload: dict) -> str:
        """Refreshes the claims of a JWT, updating expiry time."""
        jti = str(uuid.uuid4().hex)

        now = datetime.now(tz=UTC)
        exp = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

        payload.update({"jti": jti, "exp": exp})

        return jwt.encode(
            payload=payload,
            key=settings.PRIVATE_KEY_PEM,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    async def add_jti_to_blacklist(redis: RedisClient, *, jti: str, exp: int) -> bool:
        now = int(datetime.now(tz=UTC).timestamp())
        ttl = exp - now

        if ttl < 0:
            logger.warning(
                f"Token with jti={jti} is already expired.Skipping blacklist."
            )

            return False

        await redis.setex(f"session:blacklist:jti:{jti}", ttl, "Revoked")

        return True

    @staticmethod
    async def is_jti_in_blacklist(redis: RedisClient, *, jti: str) -> bool:
        return await redis.exists(f"session:blacklist:jti:{jti}")
