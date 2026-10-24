from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, EmailStr, Field

PASSWORDstr = Annotated[str, Field(..., min_length=8, max_length=128)]
PyObjectId = Annotated[str, BeforeValidator(str)]


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
