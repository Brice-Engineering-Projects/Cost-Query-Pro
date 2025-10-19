"""
src/cost_query_pro/models/user.py

Item Model
-----------
Stores user details for authentication.
"""

from sqlalchemy import Column, Integer, String, Boolean
from cost_query_pro.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)

    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin})>"
