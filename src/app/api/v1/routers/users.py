from typing import Annotated

from fastapi import (
    APIRouter, HTTPException, status,
    Depends, Body, Path, Query, Security
)

from api.dependencies import (
    get_current_user,
    limit_dependency,
)

from api.helpers import (
    get_redis_cache,
    get_user_crud,
)

from core.database import RedisCache
from core.schemas.user import (
    UserInDB, UserResponse, UserUpdate
)

from crud import UserCRUD


router = APIRouter(tags=["Users"])


@router.get(
    "/{username}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ]
)
async def read_user(
    username: Annotated[str, Path()],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
):
    """
    Returns user by `username`.
    """
    redis_key = f"user:{username}"

    user = await redis_cache.get(redis_key)

    if user:
        return UserInDB.model_validate(user)

    user = await user_crud.get_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    await redis_cache.set(redis_key, user)

    return user


@router.get(
    "/all/{role}",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponse],
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def read_users(
    role: Annotated[str, Path()],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20
):
    """
    Returns all users by role with pagination.
    """
    return await user_crud.get_multi(
        filter={"role": role},
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/{username}",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def update_user(
    username: Annotated[str, Path()],
    update_user: Annotated[UserUpdate, Body()],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
):
    """
    Updates user data by `username`.
    """
    user = await user_crud.get_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    result = await user_crud.update(
        str(user.id),
        update_user,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    await redis_cache.delete(f"user:{username}")

    return {"message": "The user account has been updated."}


@router.delete(
    "/{username}",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency)
    ]
)
async def delete_user(
    username: Annotated[str, Path()],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
):
    """
    Deletes an existing user account.
    """
    user = await user_crud.get_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if not await user_crud.delete(str(user.id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    await redis_cache.delete(f"user:{username}")

    return {"message": "The user account was deleted successfully."}
