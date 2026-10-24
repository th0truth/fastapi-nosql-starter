from unittest.mock import MagicMock

from fastapi import status


def test_create_admin(client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["admins"]
    mock_db["admins"].find_one.return_value = None
    mock_db["admins"].insert_one.return_value = MagicMock(inserted_id="id")

    response = client.post(
        "/api/v1/admin/setup",
        json={
            "first_name": "Admin",
            "middle_name": "A",
            "last_name": "Admin",
            "username": "admin",
            "email": "admin@example.com",
            "password": "password123",
            "scopes": ["admin"],
            "account_date": "2023-01-01T00:00:00",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "Admin account created successfully."


def test_admin_dashboard(authorized_client, mock_mongo_client):
    mock_users_db = mock_mongo_client.get_database("users")
    mock_products_db = mock_mongo_client.get_database("products")

    mock_users_db["admins"].count_documents.return_value = 1
    mock_users_db["sellers"].count_documents.return_value = 5
    mock_users_db["customers"].count_documents.return_value = 10

    mock_products_db.list_collection_names.return_value = ["cat1", "cat2"]

    response = authorized_client.get("/api/v1/admin/dashboard")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["users"]["admins"] == 1
    assert data["users"]["sellers"] == 5
    assert data["users"]["customers"] == 10
    assert data["products"]["categories"] == 2


def test_change_user_role(authorized_client, mock_mongo_client):
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers", "sellers"]

    # Mock user exists
    user_data = {
        "username": "cust1",
        "role": "customers",
        "scopes": ["customer"],
    }
    mock_db["customers"].find_one.return_value = user_data

    response = authorized_client.patch(
        "/api/v1/admin/users/cust1/role", json={"new_role": "sellers"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert (
        response.json()["message"]
        == "User cust1 role updated from customers to sellers"
    )
