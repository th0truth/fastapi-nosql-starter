from typing import Annotated

from api.dependencies import (
    get_current_user,
    get_mongo_client,
    get_redis_client,
    limit_dependency,
)
from core.database import MongoClient, RedisClient
from core.schemas.user import UserUpdate
from core.schemas.utils import PasswordRecovery, UpdateEmail, UpdatePassword
from core.security.utils import Hash
from crud import UserCRUD
from fastapi import APIRouter, Body, Depends, HTTPException, status

router = APIRouter(tags=["User"])


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model_exclude={"password"},
    response_model_exclude_none=True,
    dependencies=[Depends(limit_dependency)],
)
async def get_active_user(user: Annotated[dict, Depends(get_current_user)]):
    """
    Returns user data.
    """
    return user


@router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(limit_dependency)],
)
async def update_user_profile(
    user_update: Annotated[UserUpdate, Body()],
    user: Annotated[dict, Depends(get_current_user)],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Updates the current user's profile.
    """
    users_db = mongo.get_database("users")
    username = user.get("username")

    # Update the user data
    if not (
        await UserCRUD(users_db).update(
            username=username,
            update=user_update.model_dump(exclude_unset=True),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Delete user profile from Redis cache
    await redis.delete(f"cache:user:{username}:profile")

    return {"message": "The profile was updated."}


@router.patch(
    "/me/password",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(limit_dependency)],
)
async def update_password(
    update_body: Annotated[UpdatePassword, Body()],
    user: Annotated[dict, Depends(get_current_user)],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Updates the current user's password.
    """
    # Get the user email's from the MongoDB database
    users_db = mongo.get_database("users")

    username = user.get("username")

    # Verify the user's credentials
    if not (
        user := await UserCRUD(users_db).authenticate(
            username=username, plain_pwd=update_body.current_password
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update the user data
    await UserCRUD(users_db).update(
        username=username,
        update={"password": Hash.hash(plain=update_body.new_password)},
    )

    return {"message": "The password was updated."}


@router.patch(
    "/email",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(limit_dependency)],
)
async def update_email(
    user_update: Annotated[UpdateEmail, Body()],
    user: Annotated[dict, Depends(get_current_user)],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Adds an email to the user account.
    """
    # Get user's email from the MongoDB database
    users_db = mongo.get_database("users")

    if await UserCRUD(users_db).find(username=user_update.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already associated with another account.",
        )

    # Verify the user's credentials
    username = user.get("username")

    if not (
        user := await UserCRUD(users_db).authenticate(
            username=username, plain_pwd=user_update.password
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update the user data
    await UserCRUD(users_db).update(
        username=username,
        update={"email": {"address": user_update.email, "is_verified": False}},
    )

    # Delete user profile from Redis cache
    await redis.delete(f"cache:user:{username}:profile")

    return {"message": "Email added to the user account."}


@router.patch(
    "/password",
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
