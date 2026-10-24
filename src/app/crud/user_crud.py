from typing import Optional

from pymongo.asynchronous.database import AsyncDatabase

from core.config import ModelType
from core.security.utils import Hash

from .base_crud import BaseCRUD


class UserCRUD(BaseCRUD):
    def __init__(self, db: AsyncDatabase, collection: str = "users"):
        super().__init__(db)
        self.collection = collection

    async def find(self, *, username: str) -> Optional[dict]:
        return await self.db[self.collection].find_one(
            {
                "$or": [
                    {"username": {"$regex": f"^{username}$", "$options": "i"}},
                    {"email": {"$regex": f"^{username}$", "$options": "i"}},
                ]
            }
        )

    async def create(self, user: ModelType):
        user.password = Hash.hash(plain=user.password)
        await self.db[self.collection].insert_one(user.model_dump())

        return user

    async def update(self, username: str, update: dict) -> Optional[dict]:
        user = await self.find(username=username)

        if not user:
            return

        return await self.db[self.collection].find_one_and_update(
            filter={"_id": user["_id"]}, update={"$set": update}, return_document=True
        )

    async def delete(self, username: str):
        user = await self.find(username=username)

        if not user:
            return

        result = await self.db[self.collection].delete_one({"_id": user["_id"]})

        return result.deleted_count

    async def authenticate(self, *, username: str, plain_pwd: str) -> Optional[dict]:
        user = await self.find(username=username)

        if not user:
            return

        is_valid = Hash.verify(plain_pwd, user.get("password"))

        if not is_valid:
            return

        return user
