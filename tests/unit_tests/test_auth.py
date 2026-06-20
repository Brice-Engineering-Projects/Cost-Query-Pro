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


def test_login_user_form(client):
    """Register then login using OAuth2 form data."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass", "is_admin": False},
    )

    # OAuth2 form-based login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass"},
    )
    assert response.status_code == 200, response.text
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data.get("token_type", "bearer") == "bearer"


def test_login_user_json(client):
    """Register then login using JSON payload."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "testuser2", "password": "testpass", "is_admin": False},
    )

    # JSON-based login for API clients
    response = client.post(
        "/api/v1/auth/login-json",
        json={"username": "testuser2", "password": "testpass"},
    )
    assert response.status_code == 200, response.text
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data.get("token_type", "bearer") == "bearer"


def test_login_fails_with_wrong_password(client):
    """Wrong password should fail with 401 (Unauthorized)."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "testuser3", "password": "correctpass", "is_admin": False},
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser3", "password": "wrongpass"},
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body.get("code") == "INVALID_CREDENTIALS"


def test_admin_can_purge(client):
    """Admin user can purge data."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "secretpass", "is_admin": True},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secretpass"},
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
        json={"username": "user", "password": "secretpass", "is_admin": False},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user", "password": "secretpass"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/v1/admin/purge?year_cutoff=2020", headers=headers)
    assert response.status_code == 403, response.text
    assert response.json().get("code") == "ADMIN_REQUIRED"


def test_register_duplicate_username_rejected(client):
    """Registering the same username twice returns 400."""
    payload = {"username": "dupuser", "password": "passw0rd!", "is_admin": False}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400, resp.text


def test_me_returns_current_user(client):
    """GET /auth/me returns the authenticated user's own profile."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "meuser", "password": "mepassword", "is_admin": False},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "meuser", "password": "mepassword"},
    )
    token = login_resp.json()["access_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["username"] == "meuser"
    assert data["is_admin"] is False


def test_me_requires_auth(client):
    """GET /auth/me without a token returns 401."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text


def test_register_short_password_rejected(client):
    """Passwords shorter than the minimum length are rejected with 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "shortpwuser", "password": "abc", "is_admin": False},
    )
    assert resp.status_code == 422, resp.text
    assert "characters" in resp.json()["message"].lower()
