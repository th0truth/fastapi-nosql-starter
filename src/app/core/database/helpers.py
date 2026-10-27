from abc import ABC, abstractmethod


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
