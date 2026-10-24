import json
from datetime import timedelta
from typing import Annotated

from api.dependencies import (
    get_mongo_client,
    get_redis_client,
    limit_dependency,
)
from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
from core.config import settings
from core.database import MongoClient
from core.logger import get_logger

logger = get_logger(__name__)
from core.security.jwt import OAuthJWTBearer
from core.services.oauth import google_oauth
from crud import UserCRUD
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis

router = APIRouter(tags=["Authentication"])


@router.get(
    "/google", operation_id="AuthGoogle", dependencies=[Depends(limit_dependency)]
)
async def login_google(request: Request):
    """
    Redirects the user to Google's authorization page to sign in with Google.
    After consent, Google redirects back to the `/google` callback endpoint
    where the token exchange happens.
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
    mongo: Annotated[MongoClient, Depends(get_mongo_client)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    request: Request,
):
    """
    Handles the redirect callback from Google after user authentication/consent.
    """
    try:
        token: dict = await google_oauth.google.authorize_access_token(request)
    except MismatchingStateError as e:
        logger.warning("OAuth state mismatch (CSRF protection triggered): %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Authentication failed due to security check (state mismatch)."
                " Please try logging in again."
            ),
        )
    except OAuthError as e:
        logger.warning(
            "Unexpected Authlib error during token exchange: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error. Please try again later.",
        )

    if not (user := token.get("userinfo")):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The server is temporarily unable to process the request, but"
                " should recover soon."
            ),
        )

    user_email = user["email"]

    users_db = mongo.get_database("users")

    if not (user := await UserCRUD(users_db).find(username=user_email)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Couldn't validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get data from the payload
    edbo_id, role, scopes = user.get("edbo_id"), user.get("role"), user.get("scopes")

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
        key="user_role", value=role, httponly=False, secure=False, samesite="lax"
    )

    return response
