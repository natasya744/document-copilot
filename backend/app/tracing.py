"""Langfuse observability and tracing integration.

Provides tracing initialization for PydanticAI and OpenTelemetry, context
managers for structured spans, and safe fallbacks when tracing is disabled or
unconfigured.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_initialized = False


class _NoOpObservation:
    """Safe dummy observation when tracing is disabled or unconfigured."""

    def update(self, **kwargs: Any) -> None:
        pass


def init_tracing() -> None:
    """Initialize Langfuse client and PydanticAI instrumentation."""
    global _initialized
    if _initialized:
        return

    if not settings.langfuse_enabled:
        logger.info("Langfuse tracing is disabled via settings")
        return

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse credentials not configured; tracing inactive")
        return

    try:
        from langfuse import get_client
        from pydantic_ai.agent import Agent

        client = get_client()
        Agent.instrument_all()
        _initialized = True
        logger.info(
            "Langfuse tracing initialized (host=%s, env=%s)",
            settings.langfuse_host,
            settings.langfuse_environment,
        )
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse tracing: %s", exc)


def is_tracing_enabled() -> bool:
    """Return True if Langfuse tracing was successfully initialized."""
    return _initialized


def flush_traces() -> None:
    """Flush pending observations to Langfuse."""
    if not _initialized:
        return
    try:
        from langfuse import get_client

        get_client().flush()
    except Exception as exc:
        logger.warning("Failed to flush Langfuse traces: %s", exc)


@contextlib.contextmanager
def trace_observation(
    name: str,
    *,
    as_type: str = "span",
    input: Any = None,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Start an active observation (span/retriever/agent/evaluator/tool).

    Yields the observation object (supporting `.update(...)`) or a no-op dummy
    when tracing is disabled.
    """
    if not _initialized:
        yield _NoOpObservation()
        return

    try:
        from langfuse import get_client

        client = get_client()
        kwargs: dict[str, Any] = {"name": name, "as_type": as_type}
        if input is not None:
            kwargs["input"] = input
        if metadata:
            kwargs["metadata"] = metadata

        with client.start_as_current_observation(**kwargs) as obs:
            if output is not None:
                obs.update(output=output)
            yield obs
    except Exception as exc:
        logger.warning("Error in observation '%s': %s", name, exc)
        yield _NoOpObservation()


@contextlib.contextmanager
def trace_context(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Propagate trace attributes (user_id, session_id, tags) to child spans."""
    if not _initialized:
        yield
        return

    try:
        from langfuse import propagate_attributes

        kwargs: dict[str, Any] = {
            "environment": settings.langfuse_environment,
        }
        if user_id:
            kwargs["user_id"] = user_id
        if session_id:
            kwargs["session_id"] = session_id
        if tags:
            kwargs["tags"] = tags
        if metadata:
            kwargs["metadata"] = metadata

        with propagate_attributes(**kwargs):
            yield
    except Exception as exc:
        logger.warning("Error in trace_context propagate_attributes: %s", exc)
        yield
