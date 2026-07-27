"""tests/unit_tests/test_projects.py

Tests for project CRUD endpoints:
  POST   /api/v1/projects/
  GET    /api/v1/projects/
  GET    /api/v1/projects/{id}
  PUT    /api/v1/projects/{id}
  DELETE /api/v1/projects/{id}
  GET    /api/v1/projects/{id}/items
"""

# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_project(client, user_headers):
    """Creating a project returns 201 with all expected fields."""
    resp = client.post(
        "/api/v1/projects/",
        json={
            "project_name": "Main St. Sewer Rehab",
            "project_number": "202301",
            "state": "FL",
            "year": 2023,
        },
        headers=user_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_name"] == "Main St. Sewer Rehab"
    assert data["project_number"] == "202301"
    assert data["state"] == "FL"
    assert data["year"] == 2023
    assert "id" in data


def test_create_project_duplicate_number_rejected(client, user_headers):
    """Re-using an existing project_number returns 400."""
    payload = {
        "project_name": "Project A",
        "project_number": "DUPE001",
        "state": "TX",
        "year": 2022,
    }
    client.post("/api/v1/projects/", json=payload, headers=user_headers)
    resp = client.post("/api/v1/projects/", json=payload, headers=user_headers)
    assert resp.status_code == 400, resp.text


def test_create_project_requires_auth(client):
    """Unauthenticated project creation is rejected with 401."""
    resp = client.post(
        "/api/v1/projects/",
        json={
            "project_name": "No Auth",
            "project_number": "NA001",
            "state": "GA",
            "year": 2021,
        },
    )
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_projects_includes_created(client, user_headers, sample_project):
    """GET /projects/ returns a list that includes the newly created project."""
    resp = client.get("/api/v1/projects/", headers=user_headers)
    assert resp.status_code == 200, resp.text
    ids = [p["id"] for p in resp.json()]
    assert sample_project["id"] in ids


def test_list_projects_filter_by_state(client, user_headers):
    """state= filter returns only projects with the matching state."""
    client.post(
        "/api/v1/projects/",
        json={
            "project_name": "FL Project",
            "project_number": "FL001",
            "state": "FL",
            "year": 2023,
        },
        headers=user_headers,
    )
    client.post(
        "/api/v1/projects/",
        json={
            "project_name": "TX Project",
            "project_number": "TX001",
            "state": "TX",
            "year": 2023,
        },
        headers=user_headers,
    )

    resp = client.get("/api/v1/projects/", params={"state": "FL"}, headers=user_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) >= 1
    assert all(p["state"] == "FL" for p in data)


def test_list_projects_filter_by_year(client, user_headers):
    """year= filter returns only projects matching that exact year."""
    client.post(
        "/api/v1/projects/",
        json={
            "project_name": "2022 Project",
            "project_number": "Y2022",
            "state": "FL",
            "year": 2022,
        },
        headers=user_headers,
    )
    client.post(
        "/api/v1/projects/",
        json={
            "project_name": "2023 Project",
            "project_number": "Y2023",
            "state": "FL",
            "year": 2023,
        },
        headers=user_headers,
    )

    resp = client.get("/api/v1/projects/", params={"year": 2022}, headers=user_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) >= 1
    assert all(p["year"] == 2022 for p in data)


def test_list_projects_pagination(client, user_headers):
    """skip and limit control result window."""
    for i in range(5):
        client.post(
            "/api/v1/projects/",
            json={
                "project_name": f"Project {i}",
                "project_number": f"PAG{i:03d}",
                "state": "FL",
                "year": 2020 + i,
            },
            headers=user_headers,
        )

    resp = client.get(
        "/api/v1/projects/", params={"skip": 0, "limit": 2}, headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) <= 2


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


def test_get_project_by_id(client, user_headers, sample_project):
    """GET /projects/{id} returns the correct project."""
    resp = client.get(f"/api/v1/projects/{sample_project['id']}", headers=user_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == sample_project["id"]
    assert resp.json()["project_number"] == sample_project["project_number"]


def test_get_project_not_found(client, user_headers):
    """GET /projects/{id} with a nonexistent ID returns 404."""
    resp = client.get("/api/v1/projects/99999", headers=user_headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_project_name(client, user_headers, sample_project):
    """PUT /projects/{id} updates the project name."""
    resp = client.put(
        f"/api/v1/projects/{sample_project['id']}",
        json={"project_name": "Renamed Project"},
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["project_name"] == "Renamed Project"


def test_update_project_year(client, user_headers, sample_project):
    """PUT /projects/{id} can update the year."""
    resp = client.put(
        f"/api/v1/projects/{sample_project['id']}",
        json={"year": 2025},
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["year"] == 2025


def test_update_project_not_found(client, user_headers):
    """PUT /projects/{id} on a nonexistent project returns 404."""
    resp = client.put(
        "/api/v1/projects/99999",
        json={"project_name": "Ghost"},
        headers=user_headers,
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_project(client, user_headers, sample_project):
    """DELETE /projects/{id} removes the project; subsequent GET returns 404."""
    resp = client.delete(
        f"/api/v1/projects/{sample_project['id']}", headers=user_headers
    )
    assert resp.status_code == 204, resp.text

    get_resp = client.get(
        f"/api/v1/projects/{sample_project['id']}", headers=user_headers
    )
    assert get_resp.status_code == 404, get_resp.text


def test_delete_project_not_found(client, user_headers):
    """DELETE /projects/{id} on a nonexistent project returns 404."""
    resp = client.delete("/api/v1/projects/99999", headers=user_headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Items by project
# ---------------------------------------------------------------------------


def test_get_project_items_empty(client, user_headers, sample_project):
    """GET /projects/{id}/items returns an empty list when no items exist."""
    resp = client.get(
        f"/api/v1/projects/{sample_project['id']}/items", headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_get_project_items_includes_created_item(
    client, user_headers, sample_project, sample_item
):
    """GET /projects/{id}/items includes an item that was added to the project."""
    resp = client.get(
        f"/api/v1/projects/{sample_project['id']}/items", headers=user_headers
    )
    assert resp.status_code == 200, resp.text
    item_ids = [i["id"] for i in resp.json()]
    assert sample_item["id"] in item_ids


def test_get_project_items_not_found(client, user_headers):
    """GET /projects/{id}/items on a nonexistent project returns 404."""
    resp = client.get("/api/v1/projects/99999/items", headers=user_headers)
    assert resp.status_code == 404, resp.text
