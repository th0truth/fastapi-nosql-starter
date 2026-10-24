from bson import ObjectId

from .base_crud import BaseCRUD


class ProductCRUD(BaseCRUD):
    def __init__(self, db):
        super().__init__(db)

    async def get_product(self, category: str, product_id: str):
        return await self.read(category, {"_id": ObjectId(product_id)})

    async def delete_product(self, category: str, product_id: str):
        return await self.delete(category, {"_id": ObjectId(product_id)})

    async def update_product(self, category: str, product_id: str, update_data: dict):
        return await self.update(
            category, update=update_data, filter={"_id": ObjectId(product_id)}
        )
