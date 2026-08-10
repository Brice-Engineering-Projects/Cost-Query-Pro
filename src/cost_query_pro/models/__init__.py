"""src/cost_query_pro/models/__init__.py"""

# Import all models here to ensure they're registered only once
from cost_query_pro.db import Base
from cost_query_pro.models.archived_item import ArchivedItem
from cost_query_pro.models.archived_project import ArchivedProject
from cost_query_pro.models.audit_log import AuditLog
from cost_query_pro.models.data_quality_issue import DataQualityIssue
from cost_query_pro.models.item import Item
from cost_query_pro.models.llm_usage import LlmUsage
from cost_query_pro.models.project import Project
from cost_query_pro.models.upload_history import UploadHistory
from cost_query_pro.models.user import User

# Export all models
__all__ = [
    "User",
    "Project",
    "Item",
    "Base",
    "AuditLog",
    "UploadHistory",
    "DataQualityIssue",
    "LlmUsage",
    "ArchivedProject",
    "ArchivedItem",
]
