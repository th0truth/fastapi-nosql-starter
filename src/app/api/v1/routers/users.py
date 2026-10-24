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
from core.logger import get_logger

logger = get_logger(__name__)
from core.schemas.user import UserBase, UserUpdate
from crud import UserCRUD
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Security,
    status,
)

router = APIRouter(tags=["Users"])


@router.get(
    "/{username}",
    status_code=status.HTTP_200_OK,
    response_model=UserBase,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def read_user(
    username: Annotated[str, Path()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Returns user by `username`.
    """
    redis_key = f"cache:user:{username}:profile"

    # Check if user data exists in Redis cache
    if user_cache := await redis.get(redis_key):
        try:
            # Parse user data to the JSON format
            user = json.loads(user_cache)
        except json.JSONDecodeError as e:
            logger.error(
                "Error decoding user data from Redis cache: %s", e, exc_info=True
            )
    else:
        # Check if user exists in MongoDB
        users_db = mongo.get_database("users")

        if not (user := await UserCRUD(users_db).find(username=username)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        # Store user data in Redis cache
        await redis.setex(
            redis_key,
            timedelta(minutes=settings.CACHE_EXPIRE_MINUTES).seconds,
            json.dumps(user, default=str),
        )

    return user


@router.get(
    "/all/{role}",
    status_code=status.HTTP_200_OK,
    response_model=list[UserBase],
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def read_users(
    role: Annotated[str, Path()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Returns all users by role.
    """
    users_db = mongo.get_database("users")

    return await UserCRUD(users_db).read_all(role)


@router.patch(
    "/{username}",
    status_code=status.HTTP_200_OK,
    dependencies=[Security(get_current_user, scopes=["admin"])],
)
async def update_user(
    username: Annotated[str, Path()],
    update_user: Annotated[UserUpdate, Body()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Updates user data by `username`.
    """
    users_db = mongo.get_database("users")

    # Update the user data
    if not (
        await UserCRUD(users_db).update(
            username=username,
            update=update_user.model_dump(exclude_unset=True),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Delete user profile from Redis cache
    await redis.delete(f"cache:user:{username}:profile")

    return {"message": "The user account has been updated."}


@router.delete(
    "/{username}",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def delete_user(
    username: Annotated[str, Path()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[RedisClient, Depends(get_redis_client)],
):
    """
    Deletes an exiting user account.
    """

    # Delete the user account
    users_db = mongo.get_database("users")

    if not await UserCRUD(users_db).delete(username=username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    # Delete user profile from Redis cache
    await redis.delete(f"cache:user:{username}:profile")

    return {"message": "The user account was deleted successfully."}
