"""src/cost_query_pro/schemas/user.py"""

from pydantic import BaseModel, ConfigDict

class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False

class UserRead(BaseModel):
    id: int
    username: str
    is_admin: bool
    # Pydantic v2 config:
    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     orm_mode = True
