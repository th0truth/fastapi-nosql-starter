from typing import Any

from core.config import ModelType
from pymongo.asynchronous.database import AsyncDatabase


class BaseCRUD:
    def __init__(self, db: AsyncDatabase):
        self.db = db

    async def create(self, collection: str, model: ModelType):
        """Creates an object."""
        return await self.db[collection].insert_one(model.model_dump())

    async def read(self, collection: str, filter: Any):
        """Reads specific object."""
        return await self.db[collection].find_one(filter)

    async def read_all(
        self,
        collection: str,
        *,
        filter: Any = {},
        offset: int = 0,
        length: int | None = None,
    ):
        """Reads all objects."""
        objects = await self.db[collection].find(filter).to_list(length)

        return objects[offset:] if objects else []

    async def update(self, collection: str, *, update: dict, filter: Any = {}):
        """Updates an object."""
        result = await self.db[collection].update_one(filter, update={"$set": update})

        return result.modified_count

    async def update_all(
        self, collection: str, *, update: dict, filter: Any = {}
    ) -> int:
        """Updates all objects."""
        result = await self.db[collection].update_many(filter, update={"$set": update})

        return result.modified_count

    async def delete(self, collection: str, filter: Any = {}):
        """Deletes an object."""
        result = await self.db[collection].delete_one(filter)

        return result.deleted_count
