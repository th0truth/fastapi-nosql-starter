from fastapi import APIRouter

from .routers import (
    health, auth,
    google_auth,
    me, users
)

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health")
api_v1_router.include_router(google_auth.router, prefix="/auth")
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(me.router, prefix="/me")
api_v1_router.include_router(users.router, prefix="/users")
