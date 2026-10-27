from typing import TypeVar, Annotated

from pydantic import BaseModel, Field, BeforeValidator


PASSWORDstr = Annotated[str, Field(..., min_length=8, max_length=128)]
PyObjectId = Annotated[str, BeforeValidator(str)]

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
