from unittest.mock import AsyncMock, MagicMock

from fastapi import status


def test_create_customer(client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_db["customers"].find_one.return_value = None
    mock_db["customers"].insert_one.return_value = MagicMock(inserted_id="id")

    response = client.post(
        "/api/v1/customers",
        json={
            "first_name": "Test",
            "middle_name": "M",
            "last_name": "Customer",
            "username": "cust1",
            "email": "cust@example.com",
            "password": "password123",
            "account_date": "2023-01-01T00:00:00",
            "scopes": ["customer"],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert (
        response.json()["message"] == "The customer account was created successfully."
    )


def test_get_customers(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_collection = mock_db["customers"]
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "username": "c1",
                "role": "customers",
                "email": "c1@e.com",
                "first_name": "F1",
                "middle_name": "M1",
                "last_name": "L1",
                "account_date": "2023-01-01T00:00:00",
                "scopes": ["customer"],
            },
            {
                "username": "c2",
                "role": "customers",
                "email": "c2@e.com",
                "first_name": "F2",
                "middle_name": "M2",
                "last_name": "L2",
                "account_date": "2023-01-01T00:00:00",
                "scopes": ["customer"],
            },
        ]
    )
    mock_collection.find.return_value = mock_cursor

    response = authorized_client.get("/api/v1/customers")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_get_customer_by_username(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_cust = {
        "username": "cust1",
        "role": "customers",
        "email": "c@e.com",
        "first_name": "F",
        "middle_name": "M",
        "last_name": "L",
        "account_date": "2023-01-01T00:00:00",
        "scopes": ["customer"],
    }
    mock_db["customers"].find_one.return_value = mock_cust

    response = authorized_client.get("/api/v1/customers/cust1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "cust1"


def test_update_customer(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_cust = {"username": "cust1", "role": "customers"}
    mock_db["customers"].find_one.return_value = mock_cust
    mock_db["customers"].find_one_and_update.return_value = mock_cust

    response = authorized_client.patch(
        "/api/v1/customers/cust1", json={"first_name": "New Name"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The customer account has been updated."


def test_delete_customer(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]
    mock_cust = {"username": "cust1", "role": "customers"}
    mock_db["customers"].find_one.return_value = mock_cust
    mock_db["customers"].delete_one.return_value = MagicMock(deleted_count=1)

    response = authorized_client.delete("/api/v1/customers/cust1")

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["message"] == "The customer account was deleted successfully."
    )
