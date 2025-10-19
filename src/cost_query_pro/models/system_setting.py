"""
src/cost_query_pro/models/system_setting.py

System Setting Model:
---------------------
Allows storage of configurable values (e.g., “default_purge_years = 5”) directly in the DB instead of hardcoding them.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from cost_query_pro.db import Base

class SystemSetting(Base):
    __tablename__ =   "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SystemSetting(id={self.id}, key='{self.key}', value='{self.value}', description='{self.description}', timestamp='{self.timestamp}')>"

    def __str__(self):
        return f"SystemSetting(key='{self.key}', value='{self.value}', description='{self.description}')"

    def __eq__(self, other):
        if isinstance(other, SystemSetting):
            return self.key == other.key and self.value == other.value
        return False
