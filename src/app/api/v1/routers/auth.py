from datetime import timedelta
from typing import Annotated
import json

from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm

from api.dependencies import (
    get_current_user,
    limit_dependency
)

from api.helpers import (
    get_redis_cache,
    get_user_service
)

from core.database import RedisCache
from core.security import OAuthJWTBearer
from core.services import UserService

from core.schemas.token import TokenBase, TokenPayload


from crud import UserCRUD


router = APIRouter(tags=["Authentication"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[Depends(limit_dependency)],
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


    # Encode user payload to get an JWT
    token = OAuthJWTBearer.encode(
        {
            "sub": user.username,
            "role": user.role,
            "scopes": user.scopes
        }
    )

    # Store user profile in Redis cache
    await redis_cache.set(f"user:{user.username}", user)

    return TokenPayload(
        access_token=token.get("jwt"), role=user.role
    )


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[Depends(get_current_user), Depends(limit_dependency)]
)
async def auth_token(
    token: Annotated[TokenBase, Header(alias="Authorization")],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
):
    """
    Log in using an access token.
    """
    # Decode a user's JWT
    payload = OAuthJWTBearer.decode(token.access_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token."
        )

    role, jti, exp = (
        payload.get("role"),
        payload.get("jti"),
        payload.get("exp"),
    )

    # Check if jti is revoked
    if await OAuthJWTBearer.is_jti_in_blacklist(redis, jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    # Add the access token to the blacklist
    if not await OAuthJWTBearer.add_jti_to_blacklist(redis, jti=jti, exp=exp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add the token to the blacklist.",
        )

    # Refresh token
    refresh_token = await OAuthJWTBearer.refresh(payload)

    return TokenPayload(access_token=refresh_token, role=role)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user), Depends(limit_dependency)],
)
async def logout(
    token: Annotated[TokenBase, Header()],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Log out from user account.
    """
    # Decode a user's JWT
    payload = OAuthJWTBearer.decode(token=token.access_token)
    jti, exp = payload.get("jti"), payload.get("exp")

    # Check if jti is revoked
    if await OAuthJWTBearer.is_jti_in_blacklist(redis, jti=jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    # Add the access token to the blacklist
    if not await OAuthJWTBearer.add_jti_to_blacklist(redis, jti=jti, exp=exp):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An error occured while adding JWT to blacklist.",
        )

    return {"message": "Successfully logged out."}


@router.patch(
    "/password/recovery",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(limit_dependency)],
)
async def password_recovery(
    update_body: Annotated[PasswordRecovery, Body()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Password recovery for the current user.
    """
    # Update the user data
    users_db = mongo.get_database("users")

    if not (
        await UserCRUD(users_db).update(
            username=update_body.email,
            update={"password": Hash.hash(plain=update_body.new_password)},
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    return {"message": "The user's password has been recovered."}
