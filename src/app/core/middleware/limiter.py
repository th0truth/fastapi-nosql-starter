from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.util import get_remote_address

from core.config import settings

from api.helpers import get_jwt_payload


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, dispatch=None):
        super().__init__(app, dispatch)

    async def dispatch(self, request, call_next):
        payload = get_jwt_payload(request)

        if payload:
            role, jti = payload.get("role"), payload.get("jti")

            request.state.limit_value = settings.RATE_LIMITS.get(
                role, settings.RATE_LIMIT_ANONYMOUS
            )

            request.state.identifier = f"{role}:{jti}"
        else:
            request.state.limit_value = settings.RATE_LIMIT_ANONYMOUS
            request.state.identifier = f"anonymous:{get_remote_address(request)}"

        response = await call_next(request)

        return response
