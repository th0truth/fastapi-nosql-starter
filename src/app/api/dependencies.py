from typing import Annotated, Optional
from collections.abc import AsyncGenerator
from datetime import timedelta
import json

from fastapi import HTTPException, Request, status, Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings, REDIS_URI
from core.logger import get_logger

from core.database import MongoClient, RedisClient
from core.security.jwt import OAuthJWTBearer

from crud import UserCRUD


logger = get_logger(__name__)


def get_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting."""
    return getattr(
        request.state, "identifier", get_remote_address(request)
    )


limiter = Limiter(
    key_func=get_identifier,
    default_limits=list(settings.RATE_LIMIT_ANONYMOUS),
    strategy="moving-window",
    storage_uri=REDIS_URI,
    headers_enabled=False,
    swallow_errors=False,
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
)


async def get_mongo_client() -> AsyncGenerator[MongoClient, None]:
    """Dependency to get MongoDB client."""
    if not MongoClient._client:
        await MongoClient.connect()
    yield MongoClient._client


async def get_redis_client() -> AsyncGenerator[RedisClient, None]:
    """Dependency to get Redis client."""
    if not RedisClient._client:
        await RedisClient.connect()
    yield RedisClient._client


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    security_scopes: SecurityScopes,
) -> dict:
    payload = OAuthJWTBearer.decode(token=token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    username, jti = payload.get("sub"), payload.get("jti")

    if await OAuthJWTBearer.is_jti_in_blacklist(redis, jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    redis_key = f"cache:user:{username}:profile"
    user = None

    # Check if user data exists in Redis cache
    user_cache = await redis.get(redis_key)

    if user_cache:
        try:
            user = json.loads(user_cache)
        except json.JSONDecodeError as e:
            logger.error(
                "Error decoding user data from Redis cache: %s", e, exc_info=True
            )

    # If not in cache or cache failed, check MongoDB
    if not user:
        users_db = mongo.get_database("users")

        if not (
            user := await UserCRUD(users_db).find(
                username=username, exclude=["_id", "password"]
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Couldn't validate user credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        await redis.setex(
            f"cache:user:{username}:profile",
            timedelta(minutes=settings.CACHE_EXPIRE_MINUTES).seconds,
            json.dumps(user, default=str),
        )

    # Check a user's privileges
    if security_scopes.scopes:
        user_scopes = user.get("scopes", [])

        if not any(scope in security_scopes.scopes for scope in user_scopes):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not enough permissions.",
            )

    return user


def get_jwt_payload(request: Request) -> Optional[dict]:
    """Extract and decode JWT payload from Authorization header"""
    auth_token = request.headers.get("Authorization")

    if auth_token:
        access_token = auth_token.split()[1]
        payload = OAuthJWTBearer.decode(token=access_token)

        if payload:
            return payload

    return


def _set_name_from_func(func):
    """Helper to copy function name/module to decorated function."""

    def decorator(f):
        f.__name__ = func.__name__
        f.__module__ = func.__module__

        return f

    return decorator


async def limit_dependency(request: Request) -> None:
    """Dependency that applies rate limiting dynamically based on request.state."""
    limiter: Limiter = request.app.state.limiter

    @_set_name_from_func(request.scope.get("endpoint"))
    async def dummy(request: Request):
        pass

    # Get dynamic values from request.state (set by middleware)
    limit_value = getattr(request.state, "limit_value", settings.RATE_LIMIT_ANONYMOUS)

    def key_func(request: Request) -> str:
        return getattr(request.state, "identifier", request.client.host)

    endpoint_key = f"{dummy.__module__}.{dummy.__name__}"
    limiter._route_limits.pop(endpoint_key, None)

    check_request_limit = limiter.limit(
        limit_value=limit_value,
        key_func=key_func,
    )(dummy)

    await check_request_limit(request)
