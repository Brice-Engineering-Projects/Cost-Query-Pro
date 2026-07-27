"""tests/unit_tests/test_web_views.py

Covers the server-rendered dashboard view.

The dashboard was the only route calling Jinja2Templates.TemplateResponse, and
it was uncovered when Starlette was upgraded from 0.49.x to 1.x — a release
line that removed the legacy TemplateResponse(name, context) call convention.
These tests pin the supported (request, name, context) form.
"""

from typing import Any

import httpx
import pytest

from cost_query_pro.core.security import get_current_user
from cost_query_pro.main import app
from cost_query_pro.models.user import User as DBUser


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient so the view makes no network call."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False

    async def get(self, url: str) -> httpx.Response:
        return httpx.Response(200, json=[])


@pytest.fixture
def dashboard_user(client, db_session, monkeypatch):
    """Authenticate the dashboard route and stub out its upstream API call."""
    # routes.py does `import httpx`, so it holds the same module object the
    # test imported; patching the attribute here is what the view sees.
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    user = DBUser(username="dash-user", password_hash="not-a-real-hash", is_admin=False)
    db_session.add(user)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def test_dashboard_renders_template(client, dashboard_user):
    """The dashboard renders HTML rather than raising on the template call."""
    response = client.get("/dashboard")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "Dashboard" in response.text


def test_dashboard_context_reaches_template(client, dashboard_user):
    """Context passed to TemplateResponse is still available to the template."""
    response = client.get("/dashboard")

    assert response.status_code == 200, response.text
    # base.html renders `user.username` only when `user` is in the context.
    assert "dash-user" in response.text


def test_dashboard_requires_authentication(client):
    """Without a token the dashboard is rejected before rendering."""
    response = client.get("/dashboard")

    assert response.status_code == 401, response.text
