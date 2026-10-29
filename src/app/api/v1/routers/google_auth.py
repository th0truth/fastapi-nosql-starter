from typing import Annotated

from fastapi import (
    APIRouter, HTTPException,
    Request, status, Depends 
)
from fastapi.responses import RedirectResponse

from authlib.integrations.base_client.errors import (
    MismatchingStateError, OAuthError
)

from api.dependencies import limit_dependency
from api.helpers import get_redis_cache, get_user_crud

from core.config import settings
from core.database import RedisCache
from core.logger import get_logger
from core.security import OAuthJWTBearer 
from core.services import google_oauth
from crud import UserCRUD


logger = get_logger(__name__)


router = APIRouter(tags=["Authentication"])


@router.get(
    "/google",
    operation_id="AuthGoogle",
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def login_google(request: Request):
    """
    Redirects the user to Google's authorization page
    to sign in with Google.
    """
    redirect_uri = str(request.url_for("auth_google"))

    return await google_oauth.google.authorize_redirect(
        request, redirect_uri=redirect_uri
    )


@router.get(
    "/google/callback",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    operation_id="AuthGoogleCallback",
    dependencies=[
        Depends(limit_dependency)
    ]
)
async def auth_google(
    redis_cache: Annotated[RedisCache, Depends(get_redis_cache)],
    user_crud: Annotated[UserCRUD, Depends(get_user_crud)],
    request: Request
):
    """
    Handles the redirect callback from Google
    after user authentication/consent.
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
                "Authentication failed due to security check."
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

    if not user_info or "email" not in user_info:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The server is temporarily unable to process the request, but"
                " should recover soon."
            ),
        )

    user = await user_crud.get_by_email(user_info["email"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_token = OAuthJWTBearer.encode(
        payload={
            "sub": user.username,
            "role": user.role,
            "scopes": user.scopes,
        }
    )

    await redis_cache.set(f"user:{user.username}", user)

    redirect_url = settings.GOOGLE_FRONTEND_REDIRECT or settings.FRONTEND_HOST
    response = RedirectResponse(url=redirect_url)

    is_secure = redirect_url.startswith("https")

    response.set_cookie(
        key="access_token",
        value=jwt_token["jwt"],
        httponly=True,
        secure=is_secure,
        samesite="lax",
    )
    
    response.set_cookie(
        key="user_role",
        value=user.role,
        httponly=False,
        secure=is_secure,
        samesite="lax",
    )

    return response
