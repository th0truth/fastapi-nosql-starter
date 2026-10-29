from typing import Annotated

from fastapi import (
    APIRouter, HTTPException, status,
    Body, Depends, 
)

from api.dependencies import (
    get_current_user,
    limit_dependency
)

from api.helpers import (
    get_redis_cache,
    get_user_crud,
    get_user_service
)

from core.database import RedisCache
from core.services import UserService

from core.schemas.user import (
    UserInDB, UserResponse, UserUpdate
)
from core.schemas.utils import UpdatePassword

from crud import UserCRUD


router = APIRouter(tags=["Me"])


@router.get(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    response_model_exclude_none=True,
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def get_active_user(
    user: Annotated[UserInDB, Depends(get_current_user)]
):
    return user


@router.patch(
    "/",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def update_user(
    user_update: Annotated[UserUpdate, Body()],
    user_db: Annotated[UserInDB, Depends(get_current_user)],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
):
    """
    Updates the current user's profile.
    """

    result = await user_crud.update(user_db.id, user_update)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    await redis_cache.delete(f"user:{user_db.username}")

    return {"message": "The user's account has been updated."}
    

@router.patch(
    "/password",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def update_password(
    update_body: Annotated[UpdatePassword, Body()],
    user_db: Annotated[UserInDB, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    Updates the current user's password.
    """

    result = await user_service.update_password(
        user_db.username, update_body
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Something went wrong while updating password."
        )

    return {"message": "The password has been updated."}
