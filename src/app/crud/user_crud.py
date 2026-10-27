from typing import Optional
import re

from core.schemas.user import (
    UserInDB, UserCreate, UserUpdate
)

from .base_crud import BaseCRUD


class UserCRUD(
    BaseCRUD[
        UserInDB, UserCreate, UserUpdate
    ]
    ):
    def __init__(self, db):
        super().__init__(db, collection_name="users", model=UserInDB)

    async def get_by_username(self, username: str) -> Optional[UserInDB]:
        escaped_username = re.escape(username)

        doc = await self.collection.find_one(
            {
                "username": {
                    "$regex": f"^{escaped_username}$", "$options": "i"
                }
            }
        )

        if not doc:
            return

        return self.model.model_validate(doc)

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        escaped_email = re.escape(email)

        doc = await self.collection.find_one(
                {
                    "username": {
                        "$regex": f"^{escaped_email}$", "$options": "i"
                    }
                }
            )

        if not doc:
            return

        return self.model.model_validate(doc)

    async def get_by_username_or_email(
        self, indentifier: str
    ) -> Optional[UserInDB]:
        escaped_idt = re.escape(indentifier)

        doc = await self.collection.find_one(
            {
                "$or": [
                    {
                        "username": {
                            "$regex": f"^{escaped_idt}$", "$options": "i"
                        }
                    },
                    {  
                        "email": {
                            "$regex": f"^{escaped_idt}$", "$options": "i"
                        }
                    },
                ]
            }
        )

        if not doc:
            return

        return self.model.model_validate(doc)
