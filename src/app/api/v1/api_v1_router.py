from fastapi import APIRouter

from .routers import (
    health, auth,
    google_auth,
    user, users
)

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health")
api_v1_router.include_router(google_auth.router, prefix="/auth")
api_v1_router.include_router(auth.router, prefix="/auth")
api_v1_router.include_router(user.router, prefix="/user")
api_v1_router.include_router(users.router, prefix="/users")
