"""src/cost_query_pro/web/views/routes.py"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from cost_query_pro.config.settings import settings
from cost_query_pro.core.security import get_current_user
from cost_query_pro.models.user import User as DBUser

router = APIRouter()
templates = Jinja2Templates(directory="src/cost_query_pro/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, user: DBUser = Depends(get_current_user)
) -> HTMLResponse:
    async with httpx.AsyncClient(base_url=settings.api_base_url) as client:
        response = await client.get("/items/search")
    data: Any = response.json()
    # Starlette >= 0.29 takes the request as the first positional argument and
    # injects it into the template context itself; the legacy
    # TemplateResponse(name, {"request": ...}) form was removed in Starlette 1.0.
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "data": data},
    )
