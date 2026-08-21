r"""PydanticAI grounded-answer agent.

Implements the ``AnswerAgent`` protocol from ``app/chat/orchestrator.py`` with
PydanticAI: a typed agent whose structured output is an answer plus the
``chunk_id``\ s it cites, and whose three bounded tools (``search_filings``,
``read_chunk``, ``read_surrounding_chunks``) can expand the evidence set during
generation.

The grounding trust contract stays in ``app/grounding/validator.py``. This
agent only resolves the model's citations against the evidence it surfaced, so
a hallucinated ``chunk_id`` becomes a controlled ``GroundingError`` instead of a
key error. Display metadata and excerpts are always re-derived from passages.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterable, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    AgentStreamEvent,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallEvent,
    ToolResultEvent,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.chat.messages import ChatInputError, TurnMessage
from app.config import settings
from app.grounding.validator import GroundingError
from app.retrieval.queries import fetch_chunk, fetch_surrounding
from app.retrieval.retriever import HybridRetriever

INSTRUCTIONS = Path(__file__).with_name("instructions.md").read_text()

_MAX_SURROUNDING_WINDOW = 5

# Passages are shown to the model as short excerpts so a run with several
# searches stays well inside the per-minute token budget; `read_chunk` returns
# the full text when the model needs it.
_EXCERPT_CHARS = 1600
_EXCERPT_NOTE = "… [excerpt truncated — use read_chunk for the full passage]"

StatusSink = Callable[[str, str], None]

_TOOL_LABELS = {
    "search_filings": "Searching the filing corpus…",
    "read_chunk": "Reading a source passage…",
    "read_surrounding_chunks": "Reading surrounding passages…",
}


class AgentAnswer(BaseModel):
    """Structured model output: the answer and the chunks it cites."""

    answer: str
    citations: list[uuid.UUID] = []
    insufficient_evidence: bool = False


@dataclass
class DocAgentDeps:
    """Runtime deps for one agent run.

    ``evidence`` accumulates every passage surfaced to the model (the initial
    retrieval plus any tool results) so the citations can be resolved and
    validated against exactly what the model saw.
    """

    retriever: HybridRetriever
    evidence: list[SourcePassage] = field(default_factory=list)


def _format_passages(passages: Sequence[SourcePassage], *, excerpt: bool = False) -> str:
    def _text(passage: SourcePassage) -> str:
        if not excerpt or len(passage.text) <= _EXCERPT_CHARS:
            return passage.text
        return passage.text[:_EXCERPT_CHARS] + _EXCERPT_NOTE

    blocks = [
        f"CHUNK {passage.chunk_id}\n"
        f"ticker={passage.ticker} year={passage.year} "
        f"filing={passage.filing_type} section={passage.section or 'n/a'} "
        f"page={passage.page or 'n/a'}\n{_text(passage)}"
        for passage in passages
    ]
    return "\n\n".join(blocks)


async def search_filings(ctx: RunContext[DocAgentDeps], query: str, top_k: int = 3) -> str:
    """Hybrid search over the SEC filing corpus for passages on a follow-up query.

    Returns up to ``top_k`` passages with their chunk ids and document
    metadata. Use this to find evidence beyond the passages already provided.
    """
    passages = await ctx.deps.retriever.retrieve(query)
    top = passages[:top_k]
    ctx.deps.evidence.extend(top)
    return _format_passages(top, excerpt=True) or "No passages found for that query."


async def read_chunk(ctx: RunContext[DocAgentDeps], chunk_id: uuid.UUID) -> str:
    """Read the full text of a single passage by its chunk id."""
    passage = await fetch_chunk(chunk_id)
    if passage is None:
        return f"Chunk {chunk_id} not found."
    ctx.deps.evidence.append(passage)
    return _format_passages([passage])


async def read_surrounding_chunks(
    ctx: RunContext[DocAgentDeps], chunk_id: uuid.UUID, window: int = 2
) -> str:
    """Read the ``window`` passages immediately before and after a chunk id."""
    if window < 0 or window > _MAX_SURROUNDING_WINDOW:
        return f"Error: window must be between 0 and {_MAX_SURROUNDING_WINDOW}."
    passages = await fetch_surrounding(chunk_id, window)
    if not passages:
        return f"Chunk {chunk_id} not found."
    ctx.deps.evidence.extend(passages)
    return _format_passages(passages)


def _build_prompt(passages: Sequence[SourcePassage], question: str) -> str:
    context = (
        _format_passages(passages, excerpt=True)
        if passages
        else "No passages were retrieved."
    )
    return f"Retrieved source passages:\n\n{context}\n\nQuestion: {question}"


def _conversation_history(
    conversation: Sequence[TurnMessage],
) -> list[ModelRequest | ModelResponse]:
    history: list[ModelRequest | ModelResponse] = []
    for message in conversation:
        if message.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=message.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=message.content)]))
    return history


def _resolve(output: AgentAnswer, evidence: Sequence[SourcePassage]) -> GroundedAnswer:
    """Turn model output into a ``GroundedAnswer``, enforcing the citation contract.

    Mirrors ``validate_grounding``; the orchestrator re-runs that validator as
    the enforcement backstop. A hallucinated chunk id becomes a controlled
    ``GroundingError`` rather than a crash.
    """
    if output.insufficient_evidence:
        if output.citations:
            raise GroundingError("Answer declines but still cites sources")
        return GroundedAnswer(answer=output.answer, insufficient_evidence=True)

    if not output.citations:
        raise GroundingError("Answer has no citations")

    by_chunk = {passage.chunk_id: passage for passage in evidence}
    citations = []
    for chunk_id in output.citations:
        passage = by_chunk.get(chunk_id)
        if passage is None:
            raise GroundingError("Answer cites a passage that was not retrieved")
        citations.append(Citation.from_passage(passage))
    return GroundedAnswer(answer=output.answer, citations=tuple(citations))


class DocumentCopilotAgent:
    """PydanticAI-backed ``AnswerAgent`` for grounded chat."""

    def __init__(
        self, *, retriever: HybridRetriever, model: object | None = None
    ) -> None:
        self._retriever = retriever
        if model is None:
            model = OpenAIChatModel(
                settings.openai_chat_model,
                provider=OpenAIProvider(api_key=settings.openai_api_key),
            )
        self._agent = Agent(
            model,
            deps_type=DocAgentDeps,
            output_type=AgentAnswer,
            system_prompt=INSTRUCTIONS,
            tools=[search_filings, read_chunk, read_surrounding_chunks],
        )

    async def generate(
        self,
        conversation: Sequence[TurnMessage],
        passages: Sequence[SourcePassage],
        *,
        on_status: StatusSink | None = None,
    ) -> tuple[GroundedAnswer, Sequence[SourcePassage]]:
        """Answer ``conversation`` from ``passages``, returning evidence too.

        ``on_status`` receives ``(stage, label)`` pairs as the run progresses
        (model requests and individual tool calls) so the caller can stream
        live status updates to the user.
        """
        last_user_index = next(
            (
                index
                for index in range(len(conversation) - 1, -1, -1)
                if conversation[index].role == "user"
            ),
            -1,
        )
        if last_user_index == -1:
            raise ChatInputError("Request contains no user message")

        question = conversation[last_user_index].content
        history = _conversation_history(conversation[:last_user_index])
        deps = DocAgentDeps(retriever=self._retriever, evidence=list(passages))
        result = await self._agent.run(
            _build_prompt(passages, question),
            deps=deps,
            message_history=history,
            usage_limits=UsageLimits(
                tool_calls_limit=settings.agent_tool_calls_limit,
                per_request_input_tokens_limit=settings.agent_max_input_tokens,
            ),
            event_stream_handler=_agent_status_handler(on_status)
            if on_status is not None
            else None,
        )
        answer = _resolve(result.output, deps.evidence)
        return answer, deps.evidence


def _agent_status_handler(
    on_status: StatusSink,
) -> Callable[
    [RunContext[DocAgentDeps], AsyncIterable[AgentStreamEvent]], Awaitable[None]
]:
    """Build a PydanticAI event-stream handler that reports run progress live.

    Tool calls are the slow, observable steps of a run (each re-runs hybrid
    retrieval or reads chunks), so they map to human labels; returning to the
    model after a tool result is reported as drafting.
    """

    async def handler(
        ctx: RunContext[DocAgentDeps], events: AsyncIterable[AgentStreamEvent]
    ) -> None:
        del ctx
        async for event in events:
            if isinstance(event, ToolCallEvent):
                label = _TOOL_LABELS.get(
                    event.part.tool_name, f"Running {event.part.tool_name}…"
                )
                on_status("tool", label)
            elif isinstance(event, ToolResultEvent):
                on_status("generating", "Drafting a grounded answer…")

    return handler
