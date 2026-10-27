from typing import (
    Generic, Optional,
    Union, Dict, List, Any
)

from bson import ObjectId
from bson.errors import InvalidId

from pydantic import BaseModel

from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection

from constants import (
    ModelType, CreateSchemaType, UpdateSchemaType
)


class BaseCRUD(
        Generic[
            ModelType, CreateSchemaType, UpdateSchemaType
        ]
    ):
    def __init__(
        self,
        db: AsyncDatabase,
        collection_name: str,
        model: type[ModelType]
    ):
        self.db = db
        self.collection: AsyncCollection = db[collection_name]
        self.model = model

    @staticmethod
    def to_obj_id(id: str) -> Optional[ObjectId]:
        """Safely convert string to ObjectId without throwing exceptions."""
        try:
            return ObjectId(id)
        except (InvalidId, TypeError):
            return

    async def create(self, obj_in: CreateSchemaType):
        doc = obj_in.model_dump(by_alias=True)        
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        return self.model.model_validate(doc)

    async def get_by_id(
        self, id: str, projection: Optional[Dict[str, int]]
    ) -> Optional[ModelType]:
        oid = self.to_obj_id(id)

        if not oid:
            return

        doc = await self.collection.find_one(
            {"_id": oid}, projection=projection
        )

        if not doc:
            return

        return self.model.model_validate(doc)

    async def get_multi(
        self, filter: Optional[Dict[str, Any]] = None,
        skip: int = 0, limit: int = 20,
        sort: Optional[list[tuple[str, int]]] = None
    ) -> List[ModelType]:
        query = filter or {}
        cursor = self.collection.find(query).skip(skip).limit(limit)

        if sort:
            cursor = cursor.sort(sort)

        docs = await cursor.to_list(length=limit)

        return [self.model.model_validate(doc) for doc in docs]

    async def update(
        self,
        id: str,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        oid = self.to_obj_id(id)

        if not oid:
            return         

        update_data = (
            obj_in.model_dump(exclude_unset=True)
            if isinstance(obj_in, BaseModel)
            else obj_in
        )

        if not update_data:
            return await self.get_by_id(id)

        updated_doc = await self.collection.find_one_and_update(
            {"_id": oid}, {"$set": update_data},
            return_document=True
        )

        if not updated_doc:
            return

        return self.model.model_validate(updated_doc)

    async def delete(self, id: str) -> bool:
        oid = self.to_obj_id(id)

        if not oid:
            return False

        result = await self.collection.delete_one({"_id": oid})

        return result.deleted_count > 0
