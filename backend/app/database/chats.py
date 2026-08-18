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
        .insert({"id": str(uuid.uuid4()), "user_id": str(user_id), "title": title})
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


async def create_message(
    client: AsyncClient,
    *,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    sequence_number: int,
    message_json: dict | None = None,
) -> dict:
    """Insert a chat message with an explicit id (the column has no DB default)."""
    result = await (
        client.table("chat_messages")
        .insert(
            {
                "id": str(uuid.uuid4()),
                "thread_id": str(thread_id),
                "role": role,
                "content": content,
                "sequence_number": sequence_number,
                "message_json": message_json,
            }
        )
        .execute()
    )
    return result.data[0]


async def create_citation(
    client: AsyncClient,
    *,
    message_id: uuid.UUID,
    chunk_id: uuid.UUID,
    document_id: uuid.UUID,
    excerpt: str,
    metadata_: dict,
) -> dict:
    """Insert one citation record for an assistant message."""
    result = await (
        client.table("message_citations")
        .insert(
            {
                "id": str(uuid.uuid4()),
                "message_id": str(message_id),
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "excerpt": excerpt,
                "metadata": metadata_,
            }
        )
        .execute()
    )
    return result.data[0]
