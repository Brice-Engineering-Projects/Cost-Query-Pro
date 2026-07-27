"""tests/unit_tests/test_admin_users.py

Tests for admin user management endpoints:
  GET  /api/v1/admin/users/
  DELETE /api/v1/admin/users/{id}
  PUT  /api/v1/admin/users/promote/{id}
"""

# ---------------------------------------------------------------------------
# List users
# ---------------------------------------------------------------------------


def test_admin_can_list_users(client, admin_headers):
    """Admin GET /admin/users/ returns a list of users."""
    resp = client.get("/api/v1/admin/users/", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    # The admin user created by admin_headers fixture must be present
    usernames = [u["username"] for u in data]
    assert "adminuser" in usernames


def test_non_admin_cannot_list_users(client, user_headers):
    """Non-admin GET /admin/users/ is forbidden (403)."""
    resp = client.get("/api/v1/admin/users/", headers=user_headers)
    assert resp.status_code == 403, resp.text


def test_list_users_requires_auth(client):
    """Unauthenticated GET /admin/users/ is rejected with 401."""
    resp = client.get("/api/v1/admin/users/")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Delete user
# ---------------------------------------------------------------------------


def test_admin_can_delete_user(client, admin_headers):
    """Admin can delete another user; the user is then absent from the list."""
    # Register a user to be deleted
    client.post(
        "/api/v1/auth/register",
        json={"username": "todelete", "password": "passw0rd!", "is_admin": False},
    )

    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    target = next(u for u in users if u["username"] == "todelete")

    resp = client.delete(f"/api/v1/admin/users/{target['id']}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert "deleted" in resp.json()["message"].lower()

    # Confirm the user no longer appears in the list
    remaining = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    assert not any(u["username"] == "todelete" for u in remaining)


def test_admin_cannot_delete_self(client, admin_headers):
    """Admin deleting their own account returns 400."""
    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    admin_user = next(u for u in users if u["username"] == "adminuser")

    resp = client.delete(
        f"/api/v1/admin/users/{admin_user['id']}", headers=admin_headers
    )
    assert resp.status_code == 400, resp.text


def test_delete_nonexistent_user_returns_404(client, admin_headers):
    """Deleting a user ID that doesn't exist returns 404."""
    resp = client.delete("/api/v1/admin/users/99999", headers=admin_headers)
    assert resp.status_code == 404, resp.text


def test_non_admin_cannot_delete_user(client, user_headers, admin_headers):
    """Non-admin attempting to delete a user is forbidden (403)."""
    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    # Pick any user (the admin itself is fine; 403 fires before the self-check)
    target_id = users[0]["id"]

    resp = client.delete(f"/api/v1/admin/users/{target_id}", headers=user_headers)
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Promote user
# ---------------------------------------------------------------------------


def test_admin_can_promote_user(client, admin_headers):
    """Admin promotes a regular user; response shows is_admin=True."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "topromote", "password": "passw0rd!", "is_admin": False},
    )

    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    target = next(u for u in users if u["username"] == "topromote")
    assert target["is_admin"] is False

    resp = client.put(
        f"/api/v1/admin/users/promote/{target['id']}", headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_admin"] is True


def test_promote_already_admin_returns_400(client, admin_headers):
    """Promoting a user who is already an admin returns 400."""
    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    admin_user = next(u for u in users if u["username"] == "adminuser")

    resp = client.put(
        f"/api/v1/admin/users/promote/{admin_user['id']}", headers=admin_headers
    )
    assert resp.status_code == 400, resp.text


def test_promote_nonexistent_user_returns_404(client, admin_headers):
    """Promoting a user ID that doesn't exist returns 404."""
    resp = client.put("/api/v1/admin/users/promote/99999", headers=admin_headers)
    assert resp.status_code == 404, resp.text


def test_non_admin_cannot_promote_user(client, user_headers, admin_headers):
    """Non-admin attempting to promote a user is forbidden (403)."""
    users = client.get("/api/v1/admin/users/", headers=admin_headers).json()
    target_id = users[0]["id"]

    resp = client.put(f"/api/v1/admin/users/promote/{target_id}", headers=user_headers)
    assert resp.status_code == 403, resp.text
