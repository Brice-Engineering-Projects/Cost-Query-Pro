"""
src/cost_query_pro/models/system_setting.py

System Setting Model:
---------------------
Allows storage of configurable values (e.g., "default_purge_years = 5") directly in the DB instead of hardcoding them.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from cost_query_pro.db import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    def __repr__(self):
        return (
            f"<SystemSetting(id={self.id}, key='{self.key}', value='{self.value}', \n"
            f"description='{self.description}', timestamp='{self.timestamp}')>"
        )

    def __str__(self):
        return f"SystemSetting(key='{self.key}', value='{self.value}', description='{self.description}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SystemSetting):
            return self.key == other.key and self.value == other.value
        return False
