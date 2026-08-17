"""Typed query helpers for chat threads and messages.

These operate on the service-role (admin) client, which bypasses RLS, so
ownership is enforced at the API layer (see `app/api/chat.py`). RLS policies
stay in place as defense-in-depth.
"""

from __future__ import annotations

import uuid

from supabase import AsyncClient


async def list_threads(client: AsyncClient, user_id: uuid.UUID) -> list[dict]:
    """Return the user's threads, most recently updated first."""
    result = await (
        client.table("chat_threads")
        .select("*")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data or []


async def create_thread(client: AsyncClient, *, user_id: uuid.UUID, title: str) -> dict:
    """Insert a thread owned by ``user_id`` and return the created row."""
    result = await (
        client.table("chat_threads")
        .insert({"user_id": str(user_id), "title": title})
        .execute()
    )
    return result.data[0]


async def get_thread(client: AsyncClient, thread_id: uuid.UUID) -> dict | None:
    """Return one thread by id, or ``None`` when it does not exist."""
    result = await (
        client.table("chat_threads")
        .select("*")
        .eq("id", str(thread_id))
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


async def list_messages(client: AsyncClient, thread_id: uuid.UUID) -> list[dict]:
    """Return a thread's messages in chronological order."""
    result = await (
        client.table("chat_messages")
        .select("*")
        .eq("thread_id", str(thread_id))
        .order("sequence_number")
        .execute()
    )
    return result.data or []
