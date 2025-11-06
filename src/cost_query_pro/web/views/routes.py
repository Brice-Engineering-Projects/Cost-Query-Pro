"""src/cost_query_pro/web/views/routes.py"""

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from cost_query_pro.config.settings import settings
from cost_query_pro.core.security import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="src/cost_query_pro/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user)):
    async with httpx.AsyncClient(base_url=settings.api_base_url) as client:
        response = await client.get("/items/search")
    data = response.json()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "data": data},
    )
