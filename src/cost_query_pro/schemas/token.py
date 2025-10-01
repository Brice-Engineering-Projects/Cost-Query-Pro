"""src/cost_query_pro/schemas/token.py"""

from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
