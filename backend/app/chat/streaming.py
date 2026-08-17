"""AI SDK v7 UI message stream encoding (SSE).

The frontend's `DefaultChatTransport` parses the response with an
`EventSourceParserStream` (`@ai-sdk/provider-utils` → `parseJsonEventStream`),
so every event must be Server-Sent Events framed as ``data: <json>`` and each
JSON payload must match one of the `UIMessageChunk` variants (see
`frontend/node_modules/ai/dist/index.js` → `uiMessageChunkSchema`).

Only the chunk types this backend emits are produced here: `start`,
`text-start`/`text-delta`/`text-end`, a custom `data-citations` part, `finish`,
and `error` for in-band failures.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from app.assistant.outputs import GroundedAnswer

_TEXT_PART_ID = "text-0"
_CITATIONS_PART_ID = "citations-0"
_DELTA_SIZE = 128


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def error_event(detail: str) -> str:
    """An in-band error event; the client surfaces ``errorText`` to the user."""
    return _event({"type": "error", "errorText": detail})


def answer_events(answer: GroundedAnswer, message_id: str) -> Iterable[str]:
    """Encode a completed grounded answer as AI SDK stream events."""
    yield _event({"type": "start", "messageId": message_id})
    yield _event({"type": "text-start", "id": _TEXT_PART_ID})
    for delta in _text_deltas(answer.answer):
        yield _event({"type": "text-delta", "id": _TEXT_PART_ID, "delta": delta})
    yield _event({"type": "text-end", "id": _TEXT_PART_ID})
    if answer.citations:
        yield _event(
            {
                "type": "data-citations",
                "id": _CITATIONS_PART_ID,
                "data": {"citations": [citation.to_dict() for citation in answer.citations]},
            }
        )
    yield _event({"type": "finish", "finishReason": "stop"})


def _text_deltas(text: str, size: int = _DELTA_SIZE) -> Iterable[str]:
    for start in range(0, len(text), size):
        yield text[start : start + size]