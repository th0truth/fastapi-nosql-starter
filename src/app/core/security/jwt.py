from datetime import UTC, datetime, timedelta
from typing import Optional
import uuid
import jwt

from core.config import settings
from core.logger import get_logger


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
    def decode(token: str) -> Optional[dict]:
        """Decodes a JWT, returning the payload."""
        try:
            return jwt.decode(
                jwt=token,
                key=settings.PUBLIC_KEY_PEM,
                algorithms=settings.JWT_ALGORITHM,
            )
        except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
            logger.exception(f"Unable to decode JWT: {e}")

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
