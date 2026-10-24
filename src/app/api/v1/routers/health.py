from api.dependencies import limiter
from core.schemas.utils import HealthCheck
from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])


@router.get(
    "",
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
@limiter.exempt
async def healt_check():
    return HealthCheck(status="ok")
