import json
from datetime import timedelta
from typing import Annotated

from fastapi import (
    APIRouter, HTTPException,
    Request, status, Depends 
)
from fastapi.responses import RedirectResponse

from authlib.integrations.base_client.errors import (
    MismatchingStateError, OAuthError
)

from redis.asyncio import Redis

from api.dependencies import limit_dependency
from api.helpers import get_redis_client, get_user_crud

from core.config import settings
from core.logger import get_logger

from core.security import OAuthJWTBearer 
from core.services import google_oauth


from crud import UserCRUD


logger = get_logger(__name__)


router = APIRouter(tags=["Authentication"])


@router.get(
    "/google",
    operation_id="AuthGoogle",
    dependencies=[Depends(limit_dependency)]
)
async def login_google(request: Request):
    """
    Redirects the user to Google's authorization page to sign in with Google.
    """
    redirect_uri = str(request.url_for("auth_google"))

    return await google_oauth.google.authorize_redirect(
        request, redirect_uri=redirect_uri
    )


@router.get(
    "/google/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    operation_id="AuthGoogleCallback",
    dependencies=[Depends(limit_dependency)],
)
async def auth_google(
    redis: Annotated[Redis, Depends(get_redis_client)],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    request: Request,
):
    """
    Handles the redirect callback from Google after user authentication/consent.
    """
    
    try:
        token: dict = await google_oauth.google.authorize_access_token(request)
    except MismatchingStateError as e:
        logger.warning(
            f"OAuth state mismatch (CSRF protection triggered): {e}"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Authentication failed due to security check (state mismatch)."
                " Please try logging in again."
            )
        )
    except OAuthError as e:
        logger.warning(
           f"Unexpected Authlib error during token exchange: {e}",
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error. Please try again later.",
        )

    user_info = token.get("userinfo")

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The server is temporarily unable to process the request, but"
                " should recover soon."
            ),
        )

    user = user_crud.get_by_email(user_info["email"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get data from the payload
    edbo_id, role, scopes = (
        user.get("edbo_id"),
        user.get("role"),
        user.get("scopes")
    )

    # Encode user payload for get an JWT
    token = OAuthJWTBearer.encode(
        payload={"sub": str(edbo_id), "role": role, "scopes": scopes}
    )

    # Store user profile in Redis cache
    await redis.setex(
        f"cache:user:{edbo_id}:profile",
        timedelta(minutes=settings.CACHE_EXPIRE_MINUTES).seconds,
        json.dumps(user, default=str),
    )

    response = RedirectResponse(url=settings.GOOGLE_FRONTEND_REDIRECT)

    response.set_cookie(
        key="access_token",
        value=token["jwt"],
        httponly=False,
        secure=False,
        samesite="lax",
    )
    
    response.set_cookie(
        key="user_role",
        value=role,
        httponly=False,
        secure=False,
        samesite="lax"
    )

    return response
