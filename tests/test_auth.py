"""tests/test_auth.py"""


def test_register_user(client):
    """User registration returns 201 and echoes fields."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass", "is_admin": False},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_admin"] is False


def test_login_user(client):
    """Register then login."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass", "is_admin": False},
    )

    # IMPORTANT: your API expects JSON (not form-encoded)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass"},
    )
    assert response.status_code == 200, response.text
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data.get("token_type", "bearer") == "bearer"


def test_login_fails_with_wrong_password(client):
    """Wrong password should fail with 401 (Unauthorized)."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "correctpass", "is_admin": False},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpass"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    # If your API returns a different message, adjust this string:
    assert body.get("detail") in {"Invalid username or password", "Invalid credentials"}


def test_admin_can_purge(client):
    """Admin user can purge data."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "secret", "is_admin": True},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/v1/admin/purge?year_cutoff=2020", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "message" in body


def test_non_admin_cannot_purge(client):
    """Regular user cannot purge data (403)."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "user", "password": "secret", "is_admin": False},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "secret"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/v1/admin/purge?year_cutoff=2020", headers=headers)
    assert response.status_code == 403, response.text
    assert response.json().get("detail") in {
        "Not enough permissions",
        "Forbidden",
        "Admin privileges required"
    }
