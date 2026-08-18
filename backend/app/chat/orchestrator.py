"""Full chat-turn lifecycle.

Coordinates one turn: build the conversation from prior history plus the
incoming messages, retrieve passages, generate a grounded answer, enforce the
grounding contract, and — only after every step succeeds — persist the user
message, assistant message, and citations. The assistant run never writes
partial state.

Retrieval and the LLM agent are injected behind Protocols so the turn logic is
unit-testable without a database or LLM; the concrete implementations are the
hybrid retriever (`app/retrieval`) and the PydanticAI agent
(`app/assistant/agent`).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from supabase import AsyncClient

from app.assistant.agent import DocumentCopilotAgent
from app.assistant.outputs import GroundedAnswer, SourcePassage
from app.chat.messages import ChatInputError, TurnMessage, to_ui_message_json
from app.chat.streaming import answer_events, error_event
from app.database import chats
from app.grounding.validator import GroundingError, validate_grounding
from app.retrieval.retriever import HybridRetriever


class Retriever(Protocol):
    """Retrieves source passages for a query (implemented in Phase 3)."""

    async def retrieve(self, query: str) -> list[SourcePassage]: ...


class AnswerAgent(Protocol):
    """Generates a grounded answer from a conversation and retrieved passages.

    Returns the answer together with every passage it grounded on (the initial
    retrieval plus any passages its tools surfaced), so the orchestrator can
    validate citations against exactly what the model saw.
    """

    async def generate(
        self,
        conversation: Sequence[TurnMessage],
        passages: Sequence[SourcePassage],
    ) -> tuple[GroundedAnswer, Sequence[SourcePassage]]: ...


def default_retriever() -> Retriever:
    """Real hybrid retriever (Phase 3)."""
    return HybridRetriever()


def default_agent(retriever: Retriever | None = None) -> AnswerAgent:
    """Real PydanticAI grounded-answer agent (Phase 4)."""
    return DocumentCopilotAgent(retriever=retriever or default_retriever())


def _last_user_text(messages: Sequence[TurnMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    raise ChatInputError("Request contains no user message")


def _prior_turns(prior_messages: Sequence[dict]) -> list[TurnMessage]:
    return [
        TurnMessage(role=row["role"], content=row["content"]) for row in prior_messages
    ]


async def run_turn(
    *,
    client: AsyncClient,
    thread_id: uuid.UUID,
    incoming: Sequence[TurnMessage],
    prior_messages: Sequence[dict],
    retriever: Retriever,
    agent: AnswerAgent,
) -> AsyncIterator[str]:
    """Run a full turn and yield AI SDK stream events (SSE-encoded JSON).

    On retrieval/generation/grounding failure a single in-band error event is
    emitted and nothing is written. Exceptions that are not the agent's
    grounding contract propagate to the API layer.
    """
    if not incoming:
        yield error_event("Request contains no messages")
        return

    try:
        query = _last_user_text(incoming)
        conversation = _prior_turns(prior_messages) + list(incoming)
        passages = await retriever.retrieve(query)
        answer, evidence = await agent.generate(conversation, passages)
        answer = validate_grounding(answer, evidence)
    except (ChatInputError, GroundingError) as exc:
        yield error_event(exc.args[0])
        return

    next_sequence = (
        prior_messages[-1]["sequence_number"] + 1 if prior_messages else 1
    )

    if incoming[-1].role == "user":
        await chats.create_message(
            client,
            thread_id=thread_id,
            role="user",
            content=incoming[-1].content,
            sequence_number=next_sequence,
        )
        next_sequence += 1

    assistant_row = await chats.create_message(
        client,
        thread_id=thread_id,
        role="assistant",
        content=answer.answer,
        sequence_number=next_sequence,
        message_json=to_ui_message_json(
            role="assistant", content=answer.answer, citations=answer.citations
        ),
    )
    for citation in answer.citations:
        await chats.create_citation(
            client,
            message_id=uuid.UUID(assistant_row["id"]),
            chunk_id=citation.chunk_id,
            document_id=citation.document_id,
            excerpt=citation.excerpt,
            metadata_=citation.display_metadata(),
        )

    for event in answer_events(answer, assistant_row["id"]):
        yield event