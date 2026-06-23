"""tests/test_routes.py"""

import pytest

from cost_query_pro.models import Item, Project


@pytest.fixture
def create_user(client):
    def _create_user(username, password, is_admin=False):
        resp = client.post(
            "/api/v1/auth/register",
            data={"username": username, "password": password, "is_admin": is_admin},
        )

        # Register returns 201 Created
        assert resp.status_code == 201, resp.text
        return resp

    return _create_user


@pytest.fixture
def login_user(client):
    def _login_user(username, password):
        # Use form data for the OAuth2 compliant login endpoint
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login_user


def test_items_search_no_results(client, create_user, login_user):
    """Search returns empty list if no data exists."""
    create_user("testuser", "testpass", is_admin=False)
    headers = login_user("testuser", "testpass")

    response = client.get(
        "/api/v1/items/search",
        params={"q": "PVC", "state": "FL", "year_start": 2020, "year_end": 2025},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


def test_items_search_with_data(client, db_session, create_user, login_user):
    """Search returns data if items exist."""
    create_user("testuser", "testpass", is_admin=False)
    headers = login_user("testuser", "testpass")

    # Insert a fake project + item
    project = Project(
        project_name="Main St. Sewer Rehab",
        project_number="202301",
        state="FL",
        year=2023,
    )
    db_session.add(project)
    db_session.flush()

    item = Item(
        project_id=project.id,
        item_description='8" PVC Gravity Sewer',
        unit="LF",
        unit_price=45.32,
        quantity=100,
    )
    db_session.add(item)
    db_session.commit()

    response = client.get(
        "/api/v1/items/search",
        params={"q": "PVC", "state": "FL", "year_start": 2020, "year_end": 2025},
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data) == 1
    result = data[0]
    assert result["item_description"] == '8" PVC Gravity Sewer'
    assert result["unit"] == "LF"
    assert result["unit_price"] == 45.32
    assert result["project_name"] == "Main St. Sewer Rehab"
    assert result["project_number"] == "202301"
    assert result["state"] == "FL"
    assert result["year"] == 2023


def test_admin_purge(client, create_user, login_user):
    """Admin-only route works for admins."""
    create_user("admin", "secretpass", is_admin=True)
    headers = login_user("admin", "secretpass")

    response = client.delete(
        "/api/v1/admin/purge",
        params={"year_cutoff": 2020},
        headers=headers,
    )
    # purge.py returns 404 when no matching projects exist; confirms admin reached the endpoint
    assert response.status_code == 404, response.text
    assert response.json().get("code") == "NO_PROJECTS_FOUND"


def test_non_admin_forbidden(client, create_user, login_user):
    """Non-admins are forbidden."""
    create_user("user", "secretpass", is_admin=False)
    headers = login_user("user", "secretpass")

    response = client.delete(
        "/api/v1/admin/purge",
        params={"year_cutoff": 2020},
        headers=headers,
    )

    assert response.status_code == 403, response.text
    assert response.json().get("code") == "ADMIN_REQUIRED"
