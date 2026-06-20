"""
src/cost_query_pro/models/user.py

User Model
-----------
Stores user details for authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cost_query_pro.db import Base

if TYPE_CHECKING:
    from cost_query_pro.models.upload_history import UploadHistory


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    uploads: Mapped[list[UploadHistory]] = relationship(
        "UploadHistory", back_populates="user"
    )

    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin})>"
