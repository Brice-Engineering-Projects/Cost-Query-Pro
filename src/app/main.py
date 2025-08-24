"""src/app/main.py"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from src.app.config.settings import settings
from src.app.db.session import get_db

# Import routers
from src.app.api import auth, admin, projects, items

# Import models to register them

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cost Query Pro API",
    description="API for querying historical unit costs in infrastructure projects.",
    version="1.0.0",
    debug=settings.fastapi_debug
)

# Include routers (no duplicate prefixes)
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(items.router, prefix="/api/v1", tags=["items"])

@app.get("/")
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
        logger.exception("DB connectivity check failed.")
        return {
            "message": "Error connecting to DB",
            "error": str(e)
        }
