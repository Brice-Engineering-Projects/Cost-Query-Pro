"""app/tests/test_routes.py"""


def test_items_search_no_results(client):
    """
    Test that search returns empty list if no data exists.
    """
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "is_admin": False
        }
    )

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Search with no data in DB
    response = client.get(
        "/api/v1/items/search",
        params={
            "q": "PVC",
            "state": "FL",
            "year_start": 2020,
            "year_end": 2025
        },
        headers=headers
    )

    assert response.status_code == 200
    assert response.json() == []



def test_items_search_with_data(client, db_session):
    """
    Test search returns data if items exist.
    """
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "is_admin": False
        }
    )

    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Insert a fake project + item directly via DB session
    from app.models import Project, Item

    project = Project(
        project_name="Main St. Sewer Rehab",
        project_number="202301",
        state="FL",
        year=2023
    )
    db_session.add(project)
    db_session.flush()

    item = Item(
        project_id=project.id,
        item_description='8" PVC Gravity Sewer',
        unit="LF",
        unit_price=45.32
    )
    db_session.add(item)
    db_session.commit()

    # Now search for the inserted item
    response = client.get(
        "/api/v1/items/search",
        params={
            "q": "PVC",
            "state": "FL",
            "year_start": 2020,
            "year_end": 2025
        },
        headers=headers
    )

    assert response.status_code == 200

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



    def test_admin_purge(client):
    """Test Admin Only Route"""
    # Register admin
    client.post(
        "/api/v1/auth/register",
        json={"username": "admin", "password": "secret", "is_admin": True}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secret"}
    )
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/v1/admin/purge?year_cutoff=2020", headers=headers)

    assert response.status_code == 200
    assert "message" in response.json()


    def test_non_admin_forbidden(client):
    """Test forbidden for non-admin"""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={"username": "user", "password": "secret", "is_admin": False}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "user", "password": "secret"}
    )
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/v1/admin/purge?year_cutoff=2020", headers=headers)

    assert response.status_code == 403
