"""Grounded chat streaming endpoint.

Accepts AI SDK UI messages for one thread and returns an SSE stream of
`UIMessageChunk` events. Authentication and thread ownership are enforced here
(before any retrieval or LLM work); runtime failures from retrieval, the agent,
or grounding are streamed as in-band error events by the orchestrator.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from supabase import AsyncClient

from app.api.chat import _owned_thread
from app.auth.dependencies import CurrentUser, get_current_user
from app.chat.messages import UIMessage, from_ui_messages
from app.chat.orchestrator import default_agent, default_retriever, run_turn
from app.database import chats
from app.database.supabase import get_async_admin_client

router = APIRouter(prefix="/chat", tags=["chat"])


class StreamRequest(BaseModel):
    """Body for `POST /chat/stream`.

    `extra="allow"` because the AI SDK transport injects `id`, `trigger`, and
    `messageId` alongside the declared fields.
    """

    threadId: uuid.UUID
    messages: list[UIMessage]

    model_config = ConfigDict(extra="allow")


@router.post("/stream")
async def chat_stream(
    body: StreamRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    client: AsyncClient = await get_async_admin_client()
    await _owned_thread(client, body.threadId, current_user.id)
    prior_messages = await chats.list_messages(client, body.threadId)

    incoming = from_ui_messages(body.messages)
    retriever = default_retriever()
    events = run_turn(
        client=client,
        thread_id=body.threadId,
        incoming=incoming,
        prior_messages=prior_messages,
        retriever=retriever,
        agent=default_agent(retriever),
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )