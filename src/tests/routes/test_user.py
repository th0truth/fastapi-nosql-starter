from core.security.utils import Hash
from fastapi import status


def test_get_me(authorized_client):
    response = authorized_client.get("/api/v1/user/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "admin"


def test_update_profile(authorized_client, mock_mongo_client):
    # Setup mocks
    mock_db = mock_mongo_client.get_database("users")
    # find_one_and_update returns the updated document
    mock_db["admins"].find_one_and_update.return_value = {
        "username": "admin",
        "email": "updated@example.com",
    }

    # We need to make sure find() works for the check inside update()
    mock_db.list_collection_names.return_value = ["admins"]
    mock_db["admins"].find_one.return_value = {
        "username": "admin",
        "role": "admins",
    }

    response = authorized_client.patch(
        "/api/v1/user/me", json={"email": "updated@example.com"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The profile was updated."


def test_update_password(authorized_client, mock_mongo_client):
    # Need to verify current password first
    # So we need mock user with hashed password
    hashed_pwd = Hash.hash("oldpassword")
    user_data = {"username": "admin", "password": hashed_pwd, "role": "admins"}

    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["admins"]
    mock_db["admins"].find_one.return_value = user_data

    # Update mock
    mock_db["admins"].find_one_and_update.return_value = user_data

    response = authorized_client.patch(
        "/api/v1/user/me/password",
        json={
            "current_password": "oldpassword",
            "new_password": "newpassword123",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The password was updated."


def test_update_email(authorized_client, mock_mongo_client):
    # Requires password verification
    hashed_pwd = Hash.hash("password")
    user_data = {"username": "admin", "password": hashed_pwd, "role": "admins"}

    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["admins"]

    # First find check: email exists?
    # Mock find_one to return None first (email check), then return user (auth check)
    mock_collection = mock_db["admins"]
    mock_collection.find_one.side_effect = [
        None,  # Email check (no user found with this email)
        user_data,  # Auth check (user found by username)
    ]

    mock_collection.find_one_and_update.return_value = user_data

    response = authorized_client.patch(
        "/api/v1/user/email",
        json={"email": "newemail@example.com", "password": "password"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Email added to the user account."


def test_password_recovery(client, mock_mongo_client):
    # Public endpoint
    mock_db = mock_mongo_client.get_database("users")
    mock_db.list_collection_names.return_value = ["customers"]

    # Mock user found
    user_data = {"username": "user", "role": "customers"}
    mock_db["customers"].find_one.return_value = user_data
    mock_db["customers"].find_one_and_update.return_value = user_data

    response = client.patch(
        "/api/v1/user/password",
        json={"email": "user@example.com", "new_password": "newpassword123"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "The user's password has been recovered."
