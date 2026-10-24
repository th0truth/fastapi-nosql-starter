from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId
from fastapi import status


def test_create_product(seller_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("products")
    mock_db.list_collection_names.return_value = ["electronics"]

    mock_db["electronics"].insert_one.return_value = MagicMock(inserted_id="pid")

    response = seller_client.post(
        "/api/v2/products/",
        json={
            "category": "electronics",
            "item": "Laptop",
            "brand": "BrandX",
            "title": "Super Laptop",
            "description": "Fast",
            "price": 1000,
            "date": "2023-01-01T00:00:00",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == "Super Laptop"


def test_get_products(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("products")
    mock_collection = mock_db["electronics"]

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(
        return_value=[
            {
                "title": "P1",
                "category": "electronics",
                "item": "I1",
                "brand": "B1",
                "description": "D1",
                "price": 100,
            },
            {
                "title": "P2",
                "category": "electronics",
                "item": "I2",
                "brand": "B2",
                "description": "D2",
                "price": 200,
            },
        ]
    )
    mock_collection.find.return_value = mock_cursor

    response = authorized_client.get("/api/v2/products/electronics")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


def test_get_product(client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("products")
    mock_db["electronics"].find_one.return_value = {
        "_id": ObjectId(),
        "title": "Laptop",
        "category": "electronics",
        "item": "Laptop",
        "brand": "BrandX",
        "description": "Fast",
        "price": 1000,
        "date": "2023-01-01T00:00:00",
    }

    pid = str(ObjectId())
    response = client.get(f"/api/v2/products/electronics/{pid}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Laptop"


def test_update_product(seller_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("products")
    mock_db["electronics"].update_one.return_value = MagicMock(modified_count=1)

    pid = str(ObjectId())
    response = seller_client.patch(
        f"/api/v2/products/electronics/{pid}", json={"title": "Updated Laptop"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The product has been updated."


def test_delete_product(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("products")
    mock_db["electronics"].delete_one.return_value = MagicMock(deleted_count=1)

    pid = str(ObjectId())
    response = authorized_client.delete(f"/api/v2/products/electronics/{pid}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The product was deleted successfully."
