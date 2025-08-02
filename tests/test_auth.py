"""tests/test_auth.py"""

from src.app.main import app
from src.app.core.security import get_current_admin
from fastapi.testclient import TestClient


def override_get_current_admin():
    class DummyAdmin:
        username = "admin"
        is_admin = True
    return DummyAdmin()

# Apply the override
app.dependency_overrides[get_current_admin] = override_get_current_admin

client = TestClient(app)

def test_register_user(client):
    """
    Test user registration.
    """
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "is_admin": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_admin"] is False


def test_login_user(client):
    """
    Test user login.
    """
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "is_admin": False
        }
    )

    # Now login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_fails_with_wrong_password(client):
    """
    Test login fails with incorrect password.
    """
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "correctpass",
            "is_admin": False
        }
    )

    # Try to login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpass"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_admin_can_purge(client):
    """
    Test admin user can purge data.
    """
    # Register admin
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin",
            "password": "secret",
            "is_admin": True
        }
    )

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "secret"
        }
    )
    token = login_resp.json()["access_token"]
    print(token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        "/api/v1/admin/purge?year_cutoff=2020",
        headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_non_admin_cannot_purge(client):
    """
    Test regular user is forbidden from purging data.
    """
    # Register non-admin
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "user",
            "password": "secret",
            "is_admin": False
        }
    )

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "user",
            "password": "secret"
        }
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        "/api/v1/admin/purge?year_cutoff=2020",
        headers=headers
    )

    assert response.status_code == 403
