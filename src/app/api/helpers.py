from typing import Annotated, Optional

from fastapi import Depends
from fastapi.requests import Request
from slowapi.util import get_remote_address

from pymongo.asynchronous.database import AsyncDatabase 

from core.database import MongoClient, RedisClient
from core.services import UserService
from core.security.jwt import OAuthJWTBearer 

from core.database import RedisCache, RedisSession

from crud import UserCRUD


async def get_mongo_client() -> MongoClient:
    if not MongoClient._client:
        await MongoClient.connect()

    return MongoClient._client


async def _get_users_db() -> AsyncDatabase:
    client = await get_mongo_client()
    return client.get_database("users")


async def get_redis_client() -> RedisClient:
    if not RedisClient._client:
        await RedisClient.connect()
    
    return RedisClient._client


async def get_redis_cache(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> RedisCache:
    return RedisCache(redis_client)


async def get_redis_session(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> RedisSession:
    return RedisSession(redis_client)


async def get_user_crud(
    db: Annotated[AsyncDatabase, Depends(_get_users_db)]
) -> UserCRUD:
    return UserCRUD(db)


async def get_user_service(
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)]
) -> UserService:
    return UserService(user_crud, redis_cache)


def get_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting."""
    return getattr(
        request.state, "identifier", get_remote_address(request)
    )


def get_jwt_payload(request: Request) -> Optional[dict]:
    """Extract and decode JWT payload from Authorization header"""
    auth_token = request.headers.get("Authorization")

    if auth_token:
        access_token = auth_token.split()[1]
        payload = OAuthJWTBearer.decode(token=access_token)

        if payload:
            return payload

    return


def set_name_from_function(func):
    """Helper to copy function name/module to decorated function."""

    def decorator(f):
        f.__name__ = func.__name__
        f.__module__ = func.__module__

        return f

    return decorator


