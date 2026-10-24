from fastapi import APIRouter

from core.config import settings

from .v1 import api_v1_router

api_main_router = APIRouter()

api_main_router.include_router(api_v1_router, prefix=settings.API_V1_STR)
