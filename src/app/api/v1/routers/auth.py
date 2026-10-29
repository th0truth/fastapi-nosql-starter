from typing import Annotated

from fastapi import (
    APIRouter, HTTPException, status,
    Depends, Body
)
from fastapi.security import OAuth2PasswordRequestForm

from api.dependencies import (
    get_current_user,
    limit_dependency,
    oauth2_scheme
)

from api.helpers import (
    get_redis_cache,
    get_user_service,
    get_redis_session
)

from core.database import RedisCache, RedisSession
from core.security import OAuthJWTBearer
from core.services import UserService

from core.schemas.token import TokenPayload
from core.schemas.utils import PasswordRecovery


router = APIRouter(tags=["Authentication"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Log in using user credentials.a
    """
    user = await user_service.authenticate(
        form_data.username, form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


    token = OAuthJWTBearer.encode(
        {
            "sub": user.username,
            "role": user.role,
            "scopes": user.scopes
        }
    )

    await redis_cache.set(f"user:{user.username}", user)

    return TokenPayload(
        access_token=token.get("jwt"), role=user.role
    )


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[
        Depends(get_current_user),
        Depends(limit_dependency)
    ]
)
async def auth_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis_session: Annotated[RedisSession, Depends(get_redis_session)]
):
    """
    Log in using an access token.
    """
    payload = OAuthJWTBearer.decode(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role, jti, exp = (
        payload.get("role"),
        payload.get("jti"),
        payload.get("exp"),
    )

    if await redis_session.is_jti_in_blacklist(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    if not await redis_session.add_jti_to_blacklist(jti, exp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add the token to the blacklist.",
        )
    
    refresh_token = await OAuthJWTBearer.refresh(payload)

    return TokenPayload(
        access_token=refresh_token, role=role
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(get_current_user),
        Depends(limit_dependency)
    ]
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis_session: Annotated[RedisSession, Depends(get_redis_session)],
):
    """
    Log out from user account.
    """
    payload = OAuthJWTBearer.decode(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti, exp = payload.get("jti"), payload.get("exp")

    if await redis_session.is_jti_in_blacklist(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    if not await redis_session.add_jti_to_blacklist(jti, exp):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An error occured while adding JWT to blacklist.",
        )

    return {"message": "Successfully logged out."}


@router.patch(
    "/recovery",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def password_recovery(
    update_body: Annotated[PasswordRecovery, Body()],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Password recovery for the current user.
    """
    
    result = await user_service.reset_password(
        update_body.email, update_body.new_password
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    return {"message": "The user's password has been recovered."}
