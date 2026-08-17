"""Private admin endpoints for user onboarding.

These use the Supabase service-role key, so they must never be reachable from
the browser. Access is guarded by the `X-Admin-Key` header.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.database.supabase import get_async_admin_client

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

    model_config = ConfigDict(extra="forbid")


async def require_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_key)],
)
async def create_user(body: CreateUserRequest) -> dict[str, str]:
    """Create a user and send an email-verification link.

    The account is created with an unconfirmed email (`email_confirm: False`),
    so GoTrue sends a confirmation/invite link. The user must click it before
    they can sign in.
    """
    client = await get_async_admin_client()
    try:
        created = await client.auth.admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": False,
            }
        )
    except AuthApiError as exc:
        if exc.status in (
            status.HTTP_409_CONFLICT,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase auth error",
        ) from exc

    user = created.user
    return {"id": str(user.id), "email": user.email}
