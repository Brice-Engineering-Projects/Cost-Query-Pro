"""app/models/__init__.py"""
# Import all models here to ensure they're registered only once
from app.db import Base
from app.models.user import User
from app.models.project import Project
from app.models.item import Item

# Export all models
__all__ = ['User', 'Project', 'Item', 'Base']
