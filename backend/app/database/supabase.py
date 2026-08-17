"""Supabase client construction.

Two client kinds:

- **User-scoped** — anon key plus a specific user's access token. Requests go
  through PostgREST with that user's JWT, so RLS policies apply. A fresh client
  is required per request because the token is per-user.
- **Service-role (admin)** — the ``service_role`` key. Bypasses RLS for
  privileged writes; callers must still attach the authenticated ``user_id``
  explicitly so records stay user-scoped.

Sync and async variants exist because call sites differ: request-path code uses
the async clients, one-off scripts and sync helpers use the sync ones. The
service-role client is a process-wide singleton; user-scoped clients are not.
"""

from __future__ import annotations

from supabase import AsyncClient, Client, create_async_client, create_client

from app.config import settings

_sync_admin_client: Client | None = None
_async_admin_client: AsyncClient | None = None


def create_user_client(access_token: str) -> Client:
    """Sync user-scoped client bound to ``access_token`` (anon key + user JWT)."""
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client


async def create_async_user_client(access_token: str) -> AsyncClient:
    """Async user-scoped client bound to ``access_token`` (anon key + user JWT)."""
    client = await create_async_client(
        settings.supabase_url, settings.supabase_anon_key
    )
    client.postgrest.auth(access_token)
    return client


def get_admin_client() -> Client:
    """Sync service-role client. Process-wide singleton."""
    global _sync_admin_client
    if _sync_admin_client is None:
        _sync_admin_client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
    return _sync_admin_client


async def get_async_admin_client() -> AsyncClient:
    """Async service-role client. Process-wide singleton."""
    global _async_admin_client
    if _async_admin_client is None:
        _async_admin_client = await create_async_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
    return _async_admin_client
