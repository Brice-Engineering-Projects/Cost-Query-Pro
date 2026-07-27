"""tests/test_smoke.py

Basic health check — confirms FastAPI starts and the DB is reachable.
"""


def test_health_check(client):
    """GET / returns 200 and reports a successful DB connection."""
    resp = client.get("/")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "message" in data
    assert data.get("db_check") == 1
