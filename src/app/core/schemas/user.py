from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from constants import PyObjectId, PASSWORDstr


class UserInDB(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    username: str
    email: Optional[EmailStr] = None
    password: str
    role: str = "customer"
    scopes: list[str] = ["customer"]
    created_at: Optional[datetime] = None


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

class UserCreate(UserInDB):
    pass


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    scopes: Optional[list] = None
