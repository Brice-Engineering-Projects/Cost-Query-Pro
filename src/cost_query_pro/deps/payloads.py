"""
This module contains payloads for the cost query pro application.
src/cost_query_pro/deps/payloads.py
"""

from fastapi import Request, HTTPException
from cost_query_pro.schemas.user import UserCreate


async def parse_user_create(request: Request) -> UserCreate:
    ct = request.headers.get("content-type", "")
    try:
        if "application/json" in ct:
            data = await request.json()
        else:
            form = await request.form()
            # Starlette’s FormData behaves like a dict but may have lists
            data = {
                k: (v if not isinstance(v, list) else v[0])
                for k, v in form.multi_items()
            }
        return UserCreate(**data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid register payload")
