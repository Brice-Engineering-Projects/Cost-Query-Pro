"""app/schemas/__init__.py"""


from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    is_admin: bool = False

class User(UserBase):
    id: int
    is_admin: bool

    class Config:
        orm_mode = True
