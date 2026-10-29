from typing import Optional

from core.database import RedisCache
from core.security import Hash

from core.schemas.user import UserInDB, UserCreate
from core.schemas.utils import UpdatePassword

from crud import UserCRUD


class UserService:
    def __init__(
        self, user_crud: UserCRUD, redis_cache: Optional[RedisCache] = None
    ):
        self.user_crud = user_crud
        self.redis_cache = redis_cache

    async def authenticate(
        self, indentifier: str, plain_pwd: str
    ) -> Optional[UserInDB]:
        user = await self.user_crud.get_by_username_or_email(
            indentifier
        )

        if not user or not user.password:
            return

        is_verified = Hash.verify(plain_pwd, user.password)

        if is_verified is False:
            return

        return user

    async def create_user(
        self, user_in: UserCreate
    ) -> UserInDB:
        hashed = Hash.hash(user_in.password)
        user_in.password = hashed

        return await self.user_crud.create(
            user_in
        )

    async def update_password(
        self,
        username: str,
        password_obj: UpdatePassword 
    ) -> bool:
        user = await self.authenticate(
            username, password_obj.current_password
        )

        if not user:
            return False

        hashed = Hash.hash(password_obj.new_password)

        result = await self.user_crud.update(
            str(user.id), {"password": hashed}
        )

        if result and self.redis_cache:
            await self.redis_cache.delete(f"user:{username}")

        return bool(result)

    async def reset_password(
        self,
        identifier: str,
        new_password: str
    ) -> bool:
        user = await self.user_crud.get_by_username_or_email(
            identifier
        )

        if not user:
            return False

        hashed = Hash.hash(new_password)

        result = await self.user_crud.update(
            str(user.id), {"password": hashed}
        )

        if result and self.redis_cache:
            await self.redis_cache.delete(f"user:{user.username}")

        return bool(result)

        
