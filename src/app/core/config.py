from typing import Union, Annotated, Any


from pydantic import AnyUrl, BeforeValidator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> Union[list[str], str]:
    if isinstance(v, str) and not v.startswith("["):
        return [
            item.strip()
            for item in v.split(",")
            if item.strip() and not item.strip().startswith("#")
        ]
    elif isinstance(v, list | str):
        return v

    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    NAME: str = "FastAPI-NoSQL-Template"
    DESCRIPTION: str = ""
    SUMMARY: str = ""
    VERSION: str = "0.0.1"

    FRONTEND_HOST: str = "http://localhost:8000"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        return [
            str(origin).rstrip("/")
            for origin in self.BACKEND_CORS_ORIGINS
        ] + [self.FRONTEND_HOST]

    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"

    MONGO_HOSTNAME: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USERNAME: str = "root"
    MONGO_PASSWORD: str = "root"
    MONGO_DATABASE: str = "nosql"
    MONGO_MAX_POOL_SIZE: int = 100
    MONGO_MIN_POOL_SIZE: int = 10
    MONGO_CONNECT_TIMEOUT_MS: int = 10000
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = 10000
    MONGO_RETRY_WRITES: bool = True

    @computed_field
    @property
    def MONGO_URI(self) -> str:
        if ".mongodb.net" in self.MONGO_HOSTNAME:
            return (
                f"mongodb+srv://{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}"
                f"@{self.MONGO_HOSTNAME}/{self.MONGO_DATABASE}"
            )
        else:
            auth = (
                f"{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}@"
                if self.MONGO_USERNAME and self.MONGO_PASSWORD
                else ""
            )

            return (
                f"mongodb://{auth}{self.MONGO_HOSTNAME}:"
                f"{self.MONGO_PORT}/{self.MONGO_DATABASE}"
            )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USERNAME: str = ""
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    CACHE_EXPIRE_MINUTES: int = 60

    RATE_LIMIT_ANONYMOUS: str = "100/minute"
    RATE_LIMIT_USER: str = "50/minute"

    @computed_field
    @property
    def RATE_LIMITS(self) -> dict[str, str]:
        return {
            "anonymous": self.RATE_LIMIT_ANONYMOUS,
            "user": self.RATE_LIMIT_USER,
            "customer": self.RATE_LIMIT_USER,
            "seller": self.RATE_LIMIT_USER,
            "admin": self.RATE_LIMIT_USER,
        }

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_FRONTEND_REDIRECT: str | None = None

    SECRET_KEY: str = "changeme"

    JWT_ALGORITHM: str = "RS256"
    JWT_EXPIRE_MINUTES: int = 60

    PRIVATE_KEY_PEM: str = ""
    PUBLIC_KEY_PEM: str = ""


settings = Settings()


if settings.REDIS_USERNAME or settings.REDIS_PASSWORD:
    REDIS_URI = (
        f"redis://{settings.REDIS_USERNAME}:{settings.REDIS_PASSWORD}@"
        f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
else:
    REDIS_URI = (
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
