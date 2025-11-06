"""
src/cost_query_pro/models/audit_log.py

Audit Log Model:
----------------
Tracks key user and system events, such as login, purge, deletion. Essential for enterprise-grade traceability and compliance.
"""

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Text,
                        func)
from sqlalchemy.orm import relationship

from cost_query_pro.db import Base


class AuditLog(Base):
    """Tracks key user and system events, such as login, purge, deletion."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(Text)

    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', created_at='{self.created_at}')"
