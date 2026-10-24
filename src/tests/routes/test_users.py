from unittest.mock import AsyncMock, MagicMock

from fastapi import status


def test_get_user(authorized_client, mock_mongo_client):
    # Admin looking up user
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]

    mock_user = {
        "username": "testuser",
        "role": "customers",
        "email": "test@example.com",
        "first_name": "F",
        "middle_name": "M",
        "last_name": "L",
        "account_date": "2023-01-01T00:00:00",
    }
    mock_db["customers"].find_one.return_value = mock_user

    response = authorized_client.get("/api/v1/users/testuser")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "testuser"


def test_get_users_by_role(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_collection = mock_db["customers"]

    # Mock to_list
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "username": "u1",
                "role": "customers",
                "email": "u1@e.com",
                "first_name": "F1",
                "middle_name": "M1",
                "last_name": "L1",
                "account_date": "2023-01-01T00:00:00",
            },
            {
                "username": "u2",
                "role": "customers",
                "email": "u2@e.com",
                "first_name": "F2",
                "middle_name": "M2",
                "last_name": "L2",
                "account_date": "2023-01-01T00:00:00",
            },
        ]
    )
    mock_collection.find.return_value = mock_cursor

    response = authorized_client.get("/api/v1/users/all/customers")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_update_user(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_user = {"username": "testuser", "role": "customers"}
    mock_db["customers"].find_one.return_value = mock_user
    mock_db["customers"].find_one_and_update.return_value = mock_user

    response = authorized_client.patch(
        "/api/v1/users/testuser", json={"first_name": "Updated"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The user account has been updated."


def test_delete_user(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_user = {"username": "testuser", "role": "customers"}
    mock_db["customers"].find_one.return_value = mock_user
    mock_db["customers"].delete_one.return_value = MagicMock(deleted_count=1)

    response = authorized_client.delete("/api/v1/users/testuser")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The user account was deleted successfully."
