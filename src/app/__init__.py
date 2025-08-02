"""src/app/__init__.py"""

from .main import app
from .models.project import Project
from .models.item import Item

# Import and re-export Base for cleaner imports
from src.app.db import Base

__all__ = ["Base"]
