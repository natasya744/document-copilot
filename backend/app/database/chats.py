"""Typed query helpers for chat threads and messages.

These operate on the service-role (admin) client, which bypasses RLS, so
ownership is enforced at the API layer (see `app/api/chat.py`). RLS policies
stay in place as defense-in-depth.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from supabase import AsyncClient


async def list_threads(client: AsyncClient, user_id: uuid.UUID) -> list[dict]:
    """Return the user's threads with first user message, most recently updated first."""
    result = await client.rpc(
        "get_threads_with_first_message",
        {"p_user_id": str(user_id)}
    ).execute()
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
    await touch_thread(client, thread_id)
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


async def delete_thread(client: AsyncClient, thread_id: uuid.UUID) -> None:
    """Permanently delete a thread and all its messages (CASCADE via FK)."""
    await client.table("chat_threads").delete().eq("id", str(thread_id)).execute()


async def touch_thread(client: AsyncClient, thread_id: uuid.UUID) -> None:
    """Bump a thread's ``updated_at`` so recency reflects the last message."""
    await (
        client.table("chat_threads")
        .update({"updated_at": datetime.now(UTC).isoformat()})
        .eq("id", str(thread_id))
        .execute()
    )


async def purge_stale_empty_threads(
    client: AsyncClient, user_id: uuid.UUID, *, days: int = 7
) -> None:
    """Delete the user's empty "new chat" stubs older than ``days`` days.

    A stub is a thread with no messages at all — there is no user question to
    preserve. Threads that contain any real conversation are never touched,
    regardless of age.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    rows = await (
        client.table("chat_threads")
        .select("id, chat_messages(id)")
        .eq("user_id", str(user_id))
        .lt("updated_at", cutoff)
        .execute()
    )
    stale_ids = [
        str(row["id"]) for row in rows.data if not row.get("chat_messages")
    ]
    for thread_id in stale_ids:
        await delete_thread(client, uuid.UUID(thread_id))
