from typing import Annotated

from fastapi import HTTPException, Request, status, Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from slowapi import Limiter

from core.config import settings, REDIS_URI
from core.logger import get_logger

from core.schemas.user import UserInDB
from core.database import RedisCache, RedisSession
from core.security import OAuthJWTBearer

from api.helpers import (
    get_redis_cache, get_redis_session, get_user_crud,
    get_identifier, set_name_from_function
)

from crud import UserCRUD


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
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)],
    redis_session: Annotated[RedisSession, Depends(get_redis_session)],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    security_scopes: SecurityScopes
) -> UserInDB:
    payload = OAuthJWTBearer.decode(token=token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    username, jti = payload.get("sub"), payload.get("jti")

    if await redis_session.is_jti_in_blacklist(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    redis_key = f"user:{username}" 

    user = await redis_cache.get(redis_key)

    if user:
        user = UserInDB.model_validate(user)
    else:
        user = await user_crud.get_by_username(username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Couldn't validate user credentials.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        await redis_cache.set(
            redis_key, user
        )

    if security_scopes.scopes:
        if not any(
            scope in security_scopes.scopes
            for scope in user.scopes
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not enough permissions.",
            )

    return user


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
