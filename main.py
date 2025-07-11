"""app/main.py"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.settings import settings
from app.db.session import get_db



# import routers
from app.api import auth, admin

app = FastAPI(debug=settings.fastapi_debug)

# include routers
app.include_router(auth.router)
app.include_router(admin.router)

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
        return {
            "message": "Error connecting to DB",
            "error": str(e)
        }
