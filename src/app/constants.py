from typing import TypeVar, Annotated

from pydantic import BaseModel, Field, BeforeValidator


PASSWORDstr = Annotated[str, Field(..., min_length=8, max_length=128)]
PyObjectId = Annotated[str, BeforeValidator(str)]

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

LOGGER_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE
SECONDS_IN_DAY = 24 * SECONDS_IN_HOUR

CACHE_EXPIRE_SECONDS = SECONDS_IN_HOUR
