"""tests/unit_tests/conftest.py

Shared fixtures for unit tests. All fixtures are function-scoped so each test
gets a fresh, rolled-back database state.
"""

import pytest

_USER_CREDS = {"username": "regularuser", "password": "regularpass"}
_ADMIN_CREDS = {"username": "adminuser", "password": "adminpass"}


@pytest.fixture
def user_headers(client):
    """Register a regular user and return authenticated headers."""
    client.post("/api/v1/auth/register", json={**_USER_CREDS, "is_admin": False})
    resp = client.post("/api/v1/auth/login", data=_USER_CREDS)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    """Register an admin user and return authenticated headers."""
    client.post("/api/v1/auth/register", json={**_ADMIN_CREDS, "is_admin": True})
    resp = client.post("/api/v1/auth/login", data=_ADMIN_CREDS)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_project(client, user_headers):
    """Create a project via the API and return its response data."""
    resp = client.post(
        "/api/v1/projects/",
        json={
            "project_name": "Test Project",
            "project_number": "TEST001",
            "state": "FL",
            "year": 2023,
        },
        headers=user_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def sample_item(client, user_headers, sample_project):
    """Create an item in the sample project via the API and return its response data."""
    resp = client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": '8" PVC Gravity Sewer',
            "unit": "LF",
            "unit_price": 45.32,
            "quantity": 100,
        },
        headers=user_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
