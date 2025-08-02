"""src/app/models/__init__.py"""
# Import all models here to ensure they're registered only once
from src.app.db import Base
from src.app.models.user import User
from src.app.models.project import Project
from src.app.models.item import Item

# Export all models
__all__ = ['User', 'Project', 'Item', 'Base']
