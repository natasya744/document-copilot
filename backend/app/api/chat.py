"""Chat thread endpoints — create/list/get threads and list messages.

All routes require a verified Supabase user and enforce ownership in the
handler: a thread that exists but belongs to another user returns 403, a
missing thread returns 404. Wire format matches `frontend/src/lib/api.ts`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from supabase import AsyncClient

from app.api.errors import forbidden, not_found
from app.auth.dependencies import CurrentUser, get_current_user
from app.database import chats
from app.database.supabase import get_async_admin_client

router = APIRouter(prefix="/threads", tags=["threads"])


class CreateThreadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")


class ThreadOut(BaseModel):
    id: uuid.UUID
    title: str
    createdAt: datetime
    updatedAt: datetime


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    threadId: uuid.UUID
    role: str
    content: str
    sequenceNumber: int
    createdAt: datetime
    parts: list[dict] | None = None


def _to_thread(row: dict) -> ThreadOut:
    return ThreadOut(
        id=row["id"],
        title=row["title"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _to_message(row: dict) -> ChatMessageOut:
    message_json = row.get("message_json") or {}
    return ChatMessageOut(
        id=row["id"],
        threadId=row["thread_id"],
        role=row["role"],
        content=row["content"],
        sequenceNumber=row["sequence_number"],
        createdAt=row["created_at"],
        parts=message_json.get("parts"),
    )


async def _owned_thread(
    client: AsyncClient, thread_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """Fetch a thread, raising 404/403 per the ownership contract."""
    row = await chats.get_thread(client, thread_id)
    if row is None:
        raise not_found("Thread")
    if uuid.UUID(row["user_id"]) != user_id:
        raise forbidden()
    return row


@router.get("", response_model=list[ThreadOut])
async def list_threads(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ThreadOut]:
    client = await get_async_admin_client()
    rows = await chats.list_threads(client, current_user.id)
    return [_to_thread(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ThreadOut)
async def create_thread(
    body: CreateThreadRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ThreadOut:
    client = await get_async_admin_client()
    row = await chats.create_thread(client, user_id=current_user.id, title=body.title)
    return _to_thread(row)


@router.get("/{thread_id}", response_model=ThreadOut)
async def get_thread(
    thread_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ThreadOut:
    client = await get_async_admin_client()
    return _to_thread(await _owned_thread(client, thread_id, current_user.id))


@router.get("/{thread_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    thread_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ChatMessageOut]:
    client = await get_async_admin_client()
    await _owned_thread(client, thread_id, current_user.id)
    rows = await chats.list_messages(client, thread_id)
    return [_to_message(row) for row in rows]
