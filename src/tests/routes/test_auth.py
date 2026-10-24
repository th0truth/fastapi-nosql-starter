from core.security.utils import Hash
from fastapi import status


def test_login(client, mock_mongo_client):
    # Setup user in DB
    hashed_pwd = Hash.hash("password")
    user_data = {
        "_id": "test_id",
        "username": "testuser",
        "password": hashed_pwd,
        "role": "customers",
        "scopes": ["customer"],
    }

    # Mock find_one to return user
    # find() logic in UserCRUD iterates collections.
    # We mocked list_collection_names to return empty list in conftest.
    # Need to override list_collection_names and find_one.

    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]

    mock_collection = mock_db["customers"]
    mock_collection.find_one.return_value = user_data

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "password"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_collection = mock_db["customers"]
    mock_collection.find_one.return_value = None  # User not found

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "wronguser", "password": "password"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
