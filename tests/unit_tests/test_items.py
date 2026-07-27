"""tests/unit_tests/test_items.py

Tests for item CRUD and utility endpoints:
  POST   /api/v1/items/
  GET    /api/v1/items/{id}
  PUT    /api/v1/items/{id}
  DELETE /api/v1/items/{id}
  GET    /api/v1/items/units/distinct
  GET    /api/v1/items/stats/price-range
"""

# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_item(client, user_headers, sample_project):
    """Creating an item returns 201 with all expected fields."""
    resp = client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": '12" DIP Water Main',
            "unit": "LF",
            "unit_price": 78.50,
            "quantity": 500,
        },
        headers=user_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["item_description"] == '12" DIP Water Main'
    assert data["unit"] == "LF"
    assert float(data["unit_price"]) == 78.50
    assert data["project_id"] == sample_project["id"]
    assert "id" in data


def test_create_item_nonexistent_project_returns_404(client, user_headers):
    """Creating an item referencing a nonexistent project returns 404."""
    resp = client.post(
        "/api/v1/items/",
        json={
            "project_id": 99999,
            "item_description": "Orphan Item",
            "unit": "EA",
            "unit_price": 10.00,
            "quantity": 1,
        },
        headers=user_headers,
    )
    assert resp.status_code == 404, resp.text


def test_create_item_requires_auth(client, sample_project):
    """Unauthenticated item creation is rejected with 401."""
    resp = client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": "No Auth Item",
            "unit": "LF",
            "unit_price": 5.00,
            "quantity": 1,
        },
    )
    # sample_project fixture injects user_headers, but this call has no headers
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------


def test_get_item_by_id(client, user_headers, sample_item):
    """GET /items/{id} returns the item with embedded project details."""
    resp = client.get(f"/api/v1/items/{sample_item['id']}", headers=user_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == sample_item["id"]
    assert data["item_description"] == sample_item["item_description"]
    # ItemWithProject includes a nested project object
    assert "project" in data
    assert data["project"]["id"] is not None


def test_get_item_not_found(client, user_headers):
    """GET /items/{id} with a nonexistent ID returns 404."""
    resp = client.get("/api/v1/items/99999", headers=user_headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_item_price(client, user_headers, sample_item):
    """PUT /items/{id} can update the unit price."""
    resp = client.put(
        f"/api/v1/items/{sample_item['id']}",
        json={"unit_price": 99.99},
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert float(resp.json()["unit_price"]) == 99.99


def test_update_item_description(client, user_headers, sample_item):
    """PUT /items/{id} can update the item description."""
    resp = client.put(
        f"/api/v1/items/{sample_item['id']}",
        json={"item_description": "Updated Description"},
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["item_description"] == "Updated Description"


def test_update_item_to_nonexistent_project_returns_404(
    client, user_headers, sample_item
):
    """PUT /items/{id} reassigning to a nonexistent project returns 404."""
    resp = client.put(
        f"/api/v1/items/{sample_item['id']}",
        json={"project_id": 99999},
        headers=user_headers,
    )
    assert resp.status_code == 404, resp.text


def test_update_item_not_found(client, user_headers):
    """PUT /items/{id} on a nonexistent item returns 404."""
    resp = client.put(
        "/api/v1/items/99999",
        json={"unit_price": 1.00},
        headers=user_headers,
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_item(client, user_headers, sample_item):
    """DELETE /items/{id} removes the item; subsequent GET returns 404."""
    resp = client.delete(f"/api/v1/items/{sample_item['id']}", headers=user_headers)
    assert resp.status_code == 204, resp.text

    get_resp = client.get(f"/api/v1/items/{sample_item['id']}", headers=user_headers)
    assert get_resp.status_code == 404, get_resp.text


def test_delete_item_not_found(client, user_headers):
    """DELETE /items/{id} on a nonexistent item returns 404."""
    resp = client.delete("/api/v1/items/99999", headers=user_headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Distinct units
# ---------------------------------------------------------------------------


def test_distinct_units_includes_created_unit(client, user_headers, sample_item):
    """GET /items/units/distinct returns the unit from the created item."""
    resp = client.get("/api/v1/items/units/distinct", headers=user_headers)
    assert resp.status_code == 200, resp.text
    units = resp.json()
    assert isinstance(units, list)
    assert sample_item["unit"] in units


def test_distinct_units_empty_db(client, user_headers):
    """GET /items/units/distinct returns an empty list when no items exist."""
    resp = client.get("/api/v1/items/units/distinct", headers=user_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_distinct_units_no_duplicates(client, user_headers, sample_project):
    """Distinct units does not repeat the same unit even with multiple items."""
    for i in range(3):
        client.post(
            "/api/v1/items/",
            json={
                "project_id": sample_project["id"],
                "item_description": f"Item {i}",
                "unit": "LF",
                "unit_price": 10.00 + i,
                "quantity": 100,
            },
            headers=user_headers,
        )

    resp = client.get("/api/v1/items/units/distinct", headers=user_headers)
    assert resp.status_code == 200, resp.text
    units = resp.json()
    assert units.count("LF") == 1


# ---------------------------------------------------------------------------
# Price range stats
# ---------------------------------------------------------------------------


def test_price_range_returns_min_and_max(client, user_headers, sample_project):
    """GET /items/stats/price-range returns min and max prices."""
    client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": "Cheap Item",
            "unit": "EA",
            "unit_price": 10.00,
            "quantity": 100,
        },
        headers=user_headers,
    )
    client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": "Expensive Item",
            "unit": "EA",
            "unit_price": 500.00,
            "quantity": 100,
        },
        headers=user_headers,
    )

    resp = client.get("/api/v1/items/stats/price-range", headers=user_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "min_price" in data
    assert "max_price" in data
    assert float(data["min_price"]) == 10.00
    assert float(data["max_price"]) == 500.00


def test_price_range_empty_db_returns_nulls(client, user_headers):
    """GET /items/stats/price-range with no items returns null for both prices."""
    resp = client.get("/api/v1/items/stats/price-range", headers=user_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["min_price"] is None
    assert data["max_price"] is None


def test_price_range_filtered_by_keyword(client, user_headers, sample_project):
    """item_query= narrows the price range to matching descriptions only."""
    client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": "PVC Pipe 8in",
            "unit": "LF",
            "unit_price": 45.00,
            "quantity": 100,
        },
        headers=user_headers,
    )
    client.post(
        "/api/v1/items/",
        json={
            "project_id": sample_project["id"],
            "item_description": "Concrete Manhole",
            "unit": "EA",
            "unit_price": 3000.00,
            "quantity": 100,
        },
        headers=user_headers,
    )

    resp = client.get(
        "/api/v1/items/stats/price-range",
        params={"item_query": "PVC"},
        headers=user_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Only the PVC item should be in range; manhole should not affect it
    assert float(data["max_price"]) == 45.00
