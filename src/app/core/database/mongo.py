from typing import Optional

from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.errors import ConfigurationError, OperationFailure

from core.config import settings
from core.logger import get_logger

from core.security.utils import DBConnection


logger = get_logger(__name__)


class MongoClient(DBConnection):
    _instance: Optional["MongoClient"] = None
    _client: Optional[AsyncMongoClient] = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    @classmethod
    async def connect(cls):
        """Establish MongoDB connection."""
        try:
            cls._client = AsyncMongoClient(
                settings.MONGO_URI,
                maxPoolSize=settings.MONGO_MAX_POOL_SIZE,
                minPoolSize=settings.MONGO_MIN_POOL_SIZE,
                connectTimeoutMS=settings.MONGO_CONNECT_TIMEOUT_MS,
                serverSelectionTimeoutMS=settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
                retryWrites=settings.MONGO_RETRY_WRITES,
            )
            await cls._client.admin.command("ping")
            logger.info("[+] Successfully connected to MongoDB.")
        except (ConfigurationError, OperationFailure) as e:
            logger.error("Failed to connect to MongoDB: %s", e, exc_info=True)

            return

    @classmethod
    async def close(cls):
        """Close MongoDB connection."""
        if not cls._client:
            try:
                await cls._client.aclose()
                logger.info("[+] MongoDB connection closed.")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
            finally:
                cls._client = None
