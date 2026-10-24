from abc import ABC, abstractmethod

from passlib.context import CryptContext


class Hash:
    context = CryptContext(schemes=["argon2"], deprecated="auto")

    @classmethod
    def hash(cls, plain: str) -> str:
        """Return hashed string."""
        return cls.context.hash(secret=plain)

    @classmethod
    def verify(cls, plain: str, hashed: str) -> bool:
        """Return bool type of the verified string."""
        return cls.context.verify(secret=plain, hash=hashed)


class DBConnection(ABC):
    """Abstract base class for DB instance client."""

    @classmethod
    @abstractmethod
    async def connect(cls):
        """Establish instance connection."""

    @classmethod
    @abstractmethod
    async def close(cls):
        """Close instance connection."""
