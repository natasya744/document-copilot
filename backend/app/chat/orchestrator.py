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

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Protocol

from supabase import AsyncClient

from app.assistant.agent import DocumentCopilotAgent
from app.assistant.outputs import GroundedAnswer, SourcePassage
from app.chat.messages import ChatInputError, TurnMessage, to_ui_message_json
from app.chat.streaming import answer_events, error_event, status_event
from app.config import settings
from app.database import chats
from app.grounding.validator import GroundingError, validate_grounding
from app.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Shown when retrieval finds nothing relevant enough to ground an answer.
_RELEVANCE_REFUSAL = (
    "I couldn't find passages in the filings relevant enough to answer that "
    "question. Try asking about a specific company, filing, or topic covered in "
    "the corpus."
)

# Keep the agent's conversation window bounded so long threads stay within the
# model's context and per-minute token limits.
_MAX_HISTORY_MESSAGES = 6


def _best_relevance(passages: Sequence[SourcePassage]) -> float | None:
    """Highest semantic similarity among the passages, or None when unscored."""
    scored = [p.score for p in passages if p.score is not None]
    return max(scored) if scored else None


def _new_messages(
    prior: Sequence[TurnMessage], incoming: Sequence[TurnMessage]
) -> list[TurnMessage]:
    """Drop the prefix of ``incoming`` that duplicates persisted history.

    The AI SDK transport resends the full message list every turn while the
    backend also prepends the persisted history, so the overlap would double
    the conversation context. Only the trailing messages the client added are
    new.
    """
    incoming_list = list(incoming)
    if len(incoming_list) > len(prior) and incoming_list[: len(prior)] == list(prior):
        return incoming_list[len(prior) :]
    return incoming_list


class Retriever(Protocol):
    """Retrieves source passages for a query (implemented in Phase 3)."""

    async def retrieve(self, query: str) -> list[SourcePassage]: ...


class AnswerAgent(Protocol):
    """Generates a grounded answer from a conversation and retrieved passages.

    Returns the answer together with every passage it grounded on (the initial
    retrieval plus any passages its tools surfaced), so the orchestrator can
    validate citations against exactly what the model saw.

    ``on_status`` receives ``(stage, label)`` pairs as the run progresses, so
    the orchestrator can stream live progress to the client.
    """

    async def generate(
        self,
        conversation: Sequence[TurnMessage],
        passages: Sequence[SourcePassage],
        *,
        on_status: Callable[[str, str], None] | None = None,
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
        TurnMessage(role=row["role"], content=row["content"])
        for row in prior_messages[-_MAX_HISTORY_MESSAGES:]
    ]


async def _drain_statuses(
    task: asyncio.Task[tuple[GroundedAnswer, Sequence[SourcePassage]]],
    queue: asyncio.Queue[str],
) -> AsyncIterator[str]:
    """Yield status events from ``queue`` while ``task`` runs, then finish.

    The agent pushes status events into ``queue`` from its PydanticAI event
    stream (synchronously, via ``put_nowait``); this drains them as SSE frames
    while the answer task runs, so tool progress reaches the client live.
    """
    while True:
        if task.done() and queue.empty():
            return
        getter = asyncio.create_task(queue.get())
        done, _ = await asyncio.wait(
            {task, getter}, return_when=asyncio.FIRST_COMPLETED
        )
        if getter in done and not getter.cancelled():
            yield getter.result()
        else:
            getter.cancel()


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

    Pipeline progress is streamed as transient ``data-status`` events between
    each stage, and the agent's tool calls are surfaced live while it runs. On
    retrieval/generation/grounding failure a single in-band error event is
    emitted and nothing is written.
    """
    if not incoming:
        yield error_event("Request contains no messages")
        return

    try:
        prior = _prior_turns(prior_messages)
        turn = _new_messages(prior, incoming)
        if not turn:
            yield error_event("Request contains no messages")
            return
        query = _last_user_text(turn)
        conversation = prior + turn

        yield status_event("retrieving", "Searching the filing corpus…")
        passages = await retriever.retrieve(query)
        best = _best_relevance(passages)
        if best is not None and best < settings.min_relevance_score:
            yield status_event("refusing", "No relevant passages found — refusing")
            answer = GroundedAnswer(answer=_RELEVANCE_REFUSAL, insufficient_evidence=True)
            evidence = []
        else:
            yield status_event("retrieved", f"Found {len(passages)} relevant passages")
            yield status_event("generating", "Drafting a grounded answer…")
            status_queue: asyncio.Queue[str] = asyncio.Queue()

            async def _run_agent() -> tuple[GroundedAnswer, Sequence[SourcePassage]]:
                return await agent.generate(
                    conversation,
                    passages,
                    on_status=lambda stage, label: status_queue.put_nowait(
                        status_event(stage, label)
                    ),
                )

            answer_task = asyncio.create_task(_run_agent())
            async for event in _drain_statuses(answer_task, status_queue):
                yield event
            answer, evidence = answer_task.result()
            yield status_event("validating", "Verifying citations…")
            answer = validate_grounding(answer, evidence)
    except (ChatInputError, GroundingError) as exc:
        yield error_event(exc.args[0])
        return
    except Exception as exc:
        # Boundary failure from retrieval or the LLM: stream a friendly in-band
        # error instead of aborting the stream and leaving the client guessing.
        logger.warning("chat turn failed", exc_info=exc)
        yield error_event(
            "The assistant hit a problem while answering. Please try again."
        )
        return

    yield status_event("saving", "Saving to history…")
    next_sequence = (
        prior_messages[-1]["sequence_number"] + 1 if prior_messages else 1
    )

    if turn[-1].role == "user":
        await chats.create_message(
            client,
            thread_id=thread_id,
            role="user",
            content=turn[-1].content,
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