from contextlib import asynccontextmanager

from fastapi import FastAPI

from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from core.config import settings
from core.database import MongoClient, RedisClient
from core.errors import rate_limit_exceeded_handler
from core.logger import setup_logging
from core.middleware import RateLimitMiddleware

from api.api import api_main_router
from api.dependencies import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await RedisClient.connect()
    await MongoClient.connect()

    try:
        yield
    finally:
        await MongoClient.close()
        await RedisClient.close()


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.NAME,
        description=settings.DESCRIPTION,
        summary=settings.SUMMARY,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="session",
        same_site="lax",
        https_only=False,
    )

    # Attach limiter to the app
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded, rate_limit_exceeded_handler
    )

    if settings.all_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.all_cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    app.include_router(api_main_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
