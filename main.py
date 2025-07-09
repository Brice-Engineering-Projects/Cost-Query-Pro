"""app/main.py"""

from fastapi import FastAPI
from app.api import auth, admin

app = FastAPI()

app.include_router(auth.router)
app.include_router(admin.router)
