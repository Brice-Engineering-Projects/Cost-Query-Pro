"""tests/test_routes.py"""

import pytest

from cost_query_pro.models import ArchivedItem, ArchivedProject, Item, Project


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


def test_admin_purge_archives_and_deletes_records(
    client, db_session, create_user, login_user
):
    """Purge archives matching rows and removes them from live tables."""
    create_user("admin_archive", "secretpass", is_admin=True)
    headers = login_user("admin_archive", "secretpass")

    old_project = Project(
        project_name="Old Project",
        project_number="OLD-001",
        state="FL",
        year=2018,
    )
    new_project = Project(
        project_name="New Project",
        project_number="NEW-001",
        state="FL",
        year=2024,
    )
    db_session.add_all([old_project, new_project])
    db_session.flush()

    old_item_1 = Item(
        project_id=old_project.id,
        item_description="Old Item 1",
        unit="LF",
        unit_price=10.5,
        quantity=10,
    )
    old_item_2 = Item(
        project_id=old_project.id,
        item_description="Old Item 2",
        unit="EA",
        unit_price=20.0,
        quantity=2,
    )
    new_item = Item(
        project_id=new_project.id,
        item_description="New Item",
        unit="LF",
        unit_price=99.0,
        quantity=1,
    )
    db_session.add_all([old_item_1, old_item_2, new_item])
    db_session.commit()

    response = client.delete(
        "/api/v1/admin/purge",
        params={"year_cutoff": 2020},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["projects_deleted"] == 1
    assert body["items_deleted"] == 2

    remaining_old_project = (
        db_session.query(Project).filter(Project.project_number == "OLD-001").first()
    )
    assert remaining_old_project is None

    remaining_old_items = (
        db_session.query(Item)
        .filter(Item.item_description.in_(["Old Item 1", "Old Item 2"]))
        .all()
    )
    assert remaining_old_items == []

    remaining_new_project = (
        db_session.query(Project).filter(Project.project_number == "NEW-001").first()
    )
    assert remaining_new_project is not None

    archived_project = (
        db_session.query(ArchivedProject)
        .filter(ArchivedProject.project_number == "OLD-001")
        .first()
    )
    assert archived_project is not None

    archived_items = (
        db_session.query(ArchivedItem)
        .filter(ArchivedItem.project_id == archived_project.id)
        .order_by(ArchivedItem.item_description)
        .all()
    )
    assert len(archived_items) == 2
    assert archived_items[0].item_description == "Old Item 1"
    assert archived_items[1].item_description == "Old Item 2"
