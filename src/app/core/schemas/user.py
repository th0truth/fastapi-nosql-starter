from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from .utils import PASSWORDstr


class UserInitial(BaseModel):
    first_name: str
    middle_name: str
    last_name: str


class UserBase(UserInitial):
    username: str
    email: EmailStr
    role: str
    created_at: datetime


class UserPrivate(UserBase):
    account_date: datetime
    email: Optional[EmailStr] = None
    password: Optional[PASSWORDstr] = None
    scopes: list


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    scopes: Optional[list] = None
