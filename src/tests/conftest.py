from unittest.mock import AsyncMock, MagicMock

import pytest
from api.dependencies import (
    get_current_user,
    get_mongo_client,
    get_redis_client,
    limit_dependency,
)
from core.database import MongoClient
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_mongo_client():
    mock_client = MagicMock()

    # Store database mocks by name
    databases = {}

    def get_database(db_name, *args, **kwargs):
        if db_name not in databases:
            mock_db = MagicMock()

            # Store collection mocks by name per database
            collections = {}

            def get_collection(coll_name, *args, **kwargs):
                if not isinstance(coll_name, str):
                    return MagicMock()

                if coll_name not in collections:
                    coll = MagicMock()
                    coll.find_one = AsyncMock(return_value=None)
                    coll.insert_one = AsyncMock(
                        return_value=MagicMock(inserted_id="test_id")
                    )
                    coll.update_one = AsyncMock(
                        return_value=MagicMock(modified_count=1)
                    )
                    coll.update_many = AsyncMock(
                        return_value=MagicMock(modified_count=1)
                    )
                    coll.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
                    coll.find_one_and_update = AsyncMock(return_value=None)
                    coll.count_documents = AsyncMock(return_value=0)

                    mock_cursor = MagicMock()
                    mock_cursor.to_list = AsyncMock(return_value=[])
                    coll.find.return_value = mock_cursor
                    collections[coll_name] = coll

                return collections[coll_name]

            mock_db.__getitem__.side_effect = get_collection
            mock_db.get_collection.side_effect = get_collection
            mock_db.list_collection_names = AsyncMock(return_value=[])
            databases[db_name] = mock_db

        return databases[db_name]

    mock_client.get_database.side_effect = get_database
    mock_client.__getitem__.side_effect = get_database

    # Session / Transaction mocks
    mock_session = AsyncMock()
    mock_client.start_session = AsyncMock(return_value=mock_session)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_transaction = AsyncMock()
    mock_session.start_transaction = MagicMock(return_value=mock_transaction)
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)

    # To handle 'await mongo._client.start_session()' where mongo is the mock
    mock_client._client = mock_client

    # PATCH GLOBAL CLIENT
    MongoClient._client = mock_client
    MongoClient.connect = AsyncMock()
    MongoClient.close = AsyncMock()

    return mock_client


@pytest.fixture
def mock_redis_client():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = None
    mock_redis.delete.return_value = None

    return mock_redis


@pytest.fixture
def client(mock_mongo_client, mock_redis_client):
    app.dependency_overrides[get_mongo_client] = lambda: mock_mongo_client
    app.dependency_overrides[get_redis_client] = lambda: mock_redis_client
    app.dependency_overrides[limit_dependency] = lambda: None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}


@pytest.fixture
def authorized_client(client):
    """Client with mocked admin user."""
    user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "role": "admins",
        "scopes": ["admin", "seller", "customer"],
    }
    app.dependency_overrides[get_current_user] = lambda: user_data

    return client


@pytest.fixture
def seller_client(client):
    """Client with mocked seller user."""
    user_data = {
        "username": "seller",
        "email": "seller@example.com",
        "role": "sellers",
        "scopes": ["seller"],
    }
    app.dependency_overrides[get_current_user] = lambda: user_data

    return client


@pytest.fixture
def customer_client(client):
    """Client with mocked customer user."""
    user_data = {
        "username": "customer",
        "email": "customer@example.com",
        "role": "customers",
        "scopes": ["customer"],
    }
    app.dependency_overrides[get_current_user] = lambda: user_data

    return client
