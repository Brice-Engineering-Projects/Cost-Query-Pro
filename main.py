"""app/main.py"""

from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.config.settings import settings
from app.db.session import get_db

# Import models first to ensure they're registered
from app.models import User, Project, Item

# Import routers
from app.api import auth, admin, items, projects

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cost Query Pro API",
    description="API for querying historical unit costs in infrastructure projects.",
    version="1.0.0",
    debug=settings.fastapi_debug
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(items.router)
app.include_router(admin.router)

@app.get("/", status_code=status.HTTP_200_OK)
def read_root(db: Session = Depends(get_db)):
    """
    Simple health check route to confirm:
    - FastAPI is running
    - DB connection works
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "message": "Cost Query Pro is alive!",
            "db_check": result,
            "environment": settings.environment
        }
    except Exception as e:
        logger.exception("Database connectivity check failed.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Error connecting to DB",
                "error": str(e)
            }
        )
