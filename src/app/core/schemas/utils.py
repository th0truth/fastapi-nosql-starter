from typing import Optional

from pydantic import BaseModel, EmailStr

from constants import PASSWORDstr


class HealthCheck(BaseModel):
    status: str = "ok"


class UpdatePassword(BaseModel):
    current_password: PASSWORDstr
    new_password: PASSWORDstr


class UpdateEmail(BaseModel):
    email: Optional[EmailStr] = None
    password: str


class PasswordRecovery(BaseModel):
    email: str
    new_password: PASSWORDstr
