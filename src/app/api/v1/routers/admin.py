from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Security, Depends, Body

from api.dependencies import (
    get_current_user,
    get_mongo_client,
    limit_dependency,
)
from core.database import MongoClient
from core.schemas.admin import AdminBase
from crud import UserCRUD


router = APIRouter(tags=["Admin"])


@router.post(
    "/setup",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_dependency)],
)
async def create_admin_account(
    admin: Annotated[AdminBase, Body()],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Creates an initial admin account.
    """
    users_db = mongo.get_database("users")

    if await UserCRUD(users_db).find(username=admin.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin already exists.",
        )

    await UserCRUD(users_db).create(admin)

    return {"message": "Admin account created successfully."}


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def admin_dashboard(
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Returns administrative dashboard overview.
    """
    users_db = mongo.get_database("users")
    products_db = mongo.get_database("products")

    stats = {
        "users": {
            "admins": await users_db["admins"].count_documents({}),
            "sellers": await users_db["sellers"].count_documents({}),
            "customers": await users_db["customers"].count_documents({}),
        },
        "products": {
            "categories": len(await products_db.list_collection_names()),
        },
    }

    return stats


@router.patch(
    "/users/{username}/role",
    status_code=status.HTTP_200_OK,
    dependencies=[
        Security(get_current_user, scopes=["admin"]),
        Depends(limit_dependency),
    ],
)
async def change_user_role(
    username: str,
    new_role: Annotated[str, Body(embed=True)],
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
):
    """
    Changes a user's role and migrates them between collections.
    """
    users_db = mongo.get_database("users")
    user_crud = UserCRUD(users_db)

    if not (user := await user_crud.find(username=username)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    old_role = user.get("role")

    if old_role == new_role:
        return {"message": f"User is already a {new_role}"}

    # Update role in document
    user["role"] = new_role

    # Set default scopes based on role
    if new_role == "admins":
        user["scopes"] = ["admin"]
    elif new_role == "sellers":
        user["scopes"] = ["seller"]
    else:
        user["scopes"] = ["customer"]

    # Migrate document
    async with await mongo._client.start_session() as session:
        async with session.start_transaction():
            await users_db[new_role].insert_one(user)
            await users_db[old_role].delete_one({"username": username})

    return {"message": f"User {username} role updated from {old_role} to {new_role}"}
