from pydantic import BaseModel


class TokenBase(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(TokenBase):
    role: str


class TokenData(BaseModel):
    username: str
    scopes: list
