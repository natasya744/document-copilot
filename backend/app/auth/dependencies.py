"""Supabase JWT verification and current-user dependency.

Verifies the bearer token by calling Supabase Auth's user endpoint, then
exposes the authenticated identity as a FastAPI dependency. Local JWT
signature validation is deliberately avoided for the first implementation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth import AsyncGoTrueClient, User
from supabase_auth.errors import AuthApiError

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)

_auth_client: AsyncGoTrueClient | None = None


@dataclass(frozen=True)
class CurrentUser:
    """Verified identity of the authenticated Supabase user."""

    id: uuid.UUID
    email: str


def _get_auth_client() -> AsyncGoTrueClient:
    global _auth_client
    if _auth_client is None:
        _auth_client = AsyncGoTrueClient(
            url=f"{settings.supabase_url}/auth/v1",
            headers={"apikey": settings.supabase_anon_key},
            persist_session=False,
            auto_refresh_token=False,
        )
    return _auth_client


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> CurrentUser:
    """Verify the bearer JWT against Supabase Auth and return the user."""
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    try:
        response = await _get_auth_client().get_user(credentials.credentials)
    except AuthApiError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    if response is None or response.user is None:
        raise _unauthorized("Invalid or expired token")

    user: User = response.user
    if user.email is None:
        raise _unauthorized("Token does not identify a valid user")

    return CurrentUser(id=uuid.UUID(user.id), email=user.email)
