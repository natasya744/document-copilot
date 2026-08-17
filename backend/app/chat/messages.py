"""AI SDK message wire-format conversion.

The frontend sends chat turns in the AI SDK UI message format (`UIMessage`:
``id``, ``role``, ``parts``). This module owns that wire format: the Pydantic
model for HTTP input, conversion to internal turn messages for the agent, and
the UIMessage JSON stored in ``chat_messages.message_json`` for history
rehydration.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.assistant.outputs import Citation


class UIMessage(BaseModel):
    """One AI SDK UI message as sent by the frontend (extra fields allowed)."""

    id: str
    role: Literal["system", "user", "assistant", "tool"]
    parts: list[dict] = []

    model_config = ConfigDict(extra="allow")


@dataclass(frozen=True)
class TurnMessage:
    """Internal conversation message passed to the agent."""

    role: Literal["user", "assistant"]
    content: str


class ChatInputError(ValueError):
    """Raised for unsupported or contentless UI messages."""


def from_ui_message(message: UIMessage) -> TurnMessage:
    """Extract role and text content from one UI message."""
    if message.role not in ("user", "assistant"):
        raise ChatInputError(f"Unsupported message role: {message.role}")

    content = "".join(
        part["text"]
        for part in message.parts
        if part.get("type") == "text" and isinstance(part.get("text"), str)
    )
    if not content:
        raise ChatInputError("Message has no text content")

    return TurnMessage(role=message.role, content=content)


def from_ui_messages(messages: Sequence[UIMessage]) -> list[TurnMessage]:
    """Convert the request's message list, in order."""
    return [from_ui_message(message) for message in messages]


def to_ui_message_json(
    *, role: str, content: str, citations: Sequence[Citation] = ()
) -> dict:
    """Build the UIMessage JSON persisted in ``chat_messages.message_json``."""
    parts: list[dict] = [{"type": "text", "text": content}]
    if citations:
        parts.append(
            {
                "type": "data-citations",
                "data": {"citations": [citation.to_dict() for citation in citations]},
            }
        )
    return {"role": role, "parts": parts}