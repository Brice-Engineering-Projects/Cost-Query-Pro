"""src/app/schemas/__init__.py"""

from pydantic import BaseModel, ConfigDict
from typing import Optional

# ------------------------------------------------
# User schemas
# ------------------------------------------------

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    is_admin: bool

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------
# Token schema
# ------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str
