import json
from datetime import timedelta
from typing import Annotated

from api.dependencies import (
    get_current_user,
    get_mongo_client,
    get_redis_client,
    limit_dependency,
)
from core.config import settings
from core.database import MongoClient, RedisClient
from core.schemas.token import TokenBase, TokenPayload
from core.security.jwt import OAuthJWTBearer
from crud import UserCRUD
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(tags=["Authentication"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[Depends(limit_dependency)],
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Log in using user credentials.a
    """
    # Authenticate user credentials from the MongoDB database
    users_db = mongo.get_database("users")

    if not (
        user := await UserCRUD(users_db).authenticate(
            username=form_data.username,
            plain_pwd=form_data.password,
            exclude=["_id", "password"],
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get data from the payload
    username, role, scopes = (
        user.get("username"),
        user.get("role"),
        user.get("scopes"),
    )

    # Encode user payload for get an JWT
    token = OAuthJWTBearer.encode(
        payload={"sub": username, "role": role, "scopes": scopes}
    )

    # Store user profile in Redis cache
    await redis.setex(
        f"cache:user:{username}:profile",
        timedelta(minutes=settings.CACHE_EXPIRE_MINUTES).seconds,
        json.dumps(user, default=str),
    )

    return TokenPayload(access_token=token.get("jwt"), role=role)


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    response_model=TokenPayload,
    dependencies=[Depends(get_current_user), Depends(limit_dependency)],
)
async def auth_token(
    token: Annotated[TokenBase, Header(alias="Authorization")],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Log in using an access token.
    """
    # Decode a user's JWT
    if not (payload := OAuthJWTBearer.decode(token.access_token)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
        )

    # Get variables from the payload
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
