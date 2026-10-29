from typing import Optional, List
from datetime import datetime, UTC

from pydantic import (
    BaseModel, EmailStr,
    ConfigDict, Field
)

from constants import PyObjectId, PASSWORDstr


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    first_name: str
    middle_name: str
    last_name: str
    role: str
    scopes: List[str] = Field(default_factory=lambda: ["customer"])


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    scopes: Optional[List[str]] = None


class UserInDB(UserBase):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    password: str
    

class UserResponse(UserBase):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    created_at: datetime


class UserCreate(UserBase):
    password: PASSWORDstr
