from unittest.mock import AsyncMock, MagicMock

from fastapi import status


def test_create_seller(client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["sellers"]
    mock_db["sellers"].find_one.return_value = None  # No conflict

    mock_db["sellers"].insert_one.return_value = MagicMock(inserted_id="id")

    response = client.post(
        "/api/v1/sellers",
        json={
            "first_name": "Test",
            "middle_name": "M",
            "last_name": "Seller",
            "username": "seller1",
            "email": "seller@example.com",
            "password": "password123",
            "business_name": "Biz",
            "storefront_name": "Store",
            "address": "123 St",
            "identity_card": "ID123",
            "account_date": "2023-01-01T00:00:00",
            "scopes": ["seller"],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "The seller account was created successfully."


def test_get_sellers(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_collection = mock_db["sellers"]
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "username": "s1",
                "role": "sellers",
                "email": "s1@e.com",
                "first_name": "F1",
                "middle_name": "M1",
                "last_name": "L1",
                "account_date": "2023-01-01T00:00:00",
                "scopes": ["seller"],
                "business_name": "B1",
                "storefront_name": "S1",
                "address": "A1",
                "identity_card": "I1",
            },
            {
                "username": "s2",
                "role": "sellers",
                "email": "s2@e.com",
                "first_name": "F2",
                "middle_name": "M2",
                "last_name": "L2",
                "account_date": "2023-01-01T00:00:00",
                "scopes": ["seller"],
                "business_name": "B2",
                "storefront_name": "S2",
                "address": "A2",
                "identity_card": "I2",
            },
        ]
    )
    mock_collection.find.return_value = mock_cursor

    response = authorized_client.get("/api/v1/sellers")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_get_seller_by_username(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["sellers"]
    mock_seller = {
        "username": "seller1",
        "role": "sellers",
        "email": "s@e.com",
        "first_name": "F",
        "middle_name": "M",
        "last_name": "L",
        "account_date": "2023-01-01T00:00:00",
        "scopes": ["seller"],
        "business_name": "Biz",
        "storefront_name": "Store",
        "address": "123 St",
        "identity_card": "ID123",
    }
    mock_db["sellers"].find_one.return_value = mock_seller

    response = authorized_client.get("/api/v1/sellers/seller1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "seller1"


def test_update_seller(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["sellers"]
    mock_seller = {"username": "seller1", "role": "sellers"}
    mock_db["sellers"].find_one.return_value = mock_seller
    mock_db["sellers"].find_one_and_update.return_value = mock_seller

    response = authorized_client.patch(
        "/api/v1/sellers/seller1", json={"business_name": "New Biz"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The seller account has been updated."


def test_delete_seller(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["sellers"]
    mock_seller = {"username": "seller1", "role": "sellers"}
    mock_db["sellers"].find_one.return_value = mock_seller
    mock_db["sellers"].delete_one.return_value = MagicMock(deleted_count=1)

    response = authorized_client.delete("/api/v1/sellers/seller1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The seller account was deleted successfully."
