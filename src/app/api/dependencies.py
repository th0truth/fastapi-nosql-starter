from typing import Annotated, Optional
from datetime import timedelta
import json

from fastapi import HTTPException, Request, status, Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from slowapi import Limiter

from core.config import settings, REDIS_URI
from core.logger import get_logger

from core.database import RedisClient, RedisCache
from core.security.jwt import OAuthJWTBearer
from core.services import UserService

from api.helpers import (
    get_redis_client, get_redis_cache,
    get_user_service, get_identifier,
    set_name_from_function
)


logger = get_logger(__name__)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
)

limiter = Limiter(
    key_func=get_identifier,
    default_limits=list(settings.RATE_LIMIT_ANONYMOUS),
    strategy="moving-window",
    storage_uri=REDIS_URI,
    headers_enabled=False,
    swallow_errors=False,
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    security_scopes: SecurityScopes,
) -> dict:
    payload = OAuthJWTBearer.decode(token=token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    username, jti = payload.get("sub"), payload.get("jti")

    if await OAuthJWTBearer.is_jti_in_blacklist(redis_client, jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    redis_key = f"cache:user:{username}:profile"
    user = None

    

    # # If not in cache or cache failed, check MongoDB
    # if not user:
    #     if not (
    #         user := await UserCRUD(users_db).find(
    #             username=username, exclude=["_id", "password"]
    #         )
    #     ):
    #         raise HTTPException(
    #             status_code=status.HTTP_401_UNAUTHORIZED,
    #             detail="Couldn't validate user credentials.",
    #             headers={"WWW-Authenticate": "Bearer"},
    #         )

    #     await redis.setex(
    #         f"cache:user:{username}:profile",
    #         timedelta(minutes=settings.CACHE_EXPIRE_MINUTES).seconds,
    #         json.dumps(user, default=str),
    #     )

    # # Check a user's privileges
    # if security_scopes.scopes:
    #     user_scopes = user.get("scopes", [])

    #     if not any(scope in security_scopes.scopes for scope in user_scopes):
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="Not enough permissions.",
    #         )

    # return user


def get_jwt_payload(request: Request) -> Optional[dict]:
    """Extract and decode JWT payload from Authorization header"""
    auth_token = request.headers.get("Authorization")

    if auth_token:
        access_token = auth_token.split()[1]
        payload = OAuthJWTBearer.decode(token=access_token)

        if payload:
            return payload

    return


async def limit_dependency(request: Request) -> None:
    """
    Dependency that applies rate limiting dynamically based on request.state.
    """
    limiter: Limiter = request.app.state.limiter

    @set_name_from_function(request.scope.get("endpoint"))
    async def dummy(request: Request):
        pass

    # Get dynamic values from request.state (set by middleware)
    limit_value = getattr(
        request.state, "limit_value", settings.RATE_LIMIT_ANONYMOUS
    )

    def key_func(request: Request) -> str:
        return getattr(
            request.state, "identifier", request.client.host
        )

    endpoint_key = f"{dummy.__module__}.{dummy.__name__}"
    limiter._route_limits.pop(endpoint_key, None)

    check_request_limit = limiter.limit(
        limit_value=limit_value,
        key_func=key_func,
    )(dummy)

    await check_request_limit(request)
