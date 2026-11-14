"""Unit tests for Langfuse tracing helpers."""

from unittest.mock import MagicMock, patch

import pytest

from app.tracing import (
    _NoOpObservation,
    flush_traces,
    init_tracing,
    is_tracing_enabled,
    trace_context,
    trace_observation,
)


def test_noop_observation_update():
    obs = _NoOpObservation()
    # Should not raise
    obs.update(output={"test": 123}, level="DEFAULT")


def test_init_tracing_disabled():
    with patch("app.tracing.settings.langfuse_enabled", False):
        with patch("app.tracing._initialized", False):
            init_tracing()
            assert not is_tracing_enabled()


def test_init_tracing_missing_keys():
    with (
        patch("app.tracing.settings.langfuse_enabled", True),
        patch("app.tracing.settings.langfuse_public_key", None),
        patch("app.tracing.settings.langfuse_secret_key", None),
        patch("app.tracing._initialized", False),
    ):
        init_tracing()
        assert not is_tracing_enabled()


def test_trace_observation_disabled_yields_noop():
    with patch("app.tracing._initialized", False):
        with trace_observation("test-obs", as_type="span") as obs:
            assert isinstance(obs, _NoOpObservation)
            obs.update(output="noop")


def test_trace_context_disabled():
    with patch("app.tracing._initialized", False):
        with trace_context(user_id="u1", session_id="s1"):
            pass


def test_flush_traces_disabled():
    with patch("app.tracing._initialized", False):
        # Should not raise or call get_client
        flush_traces()


def test_flush_traces_enabled():
    mock_client = MagicMock()
    with patch("app.tracing._initialized", True):
        with patch("langfuse.get_client", return_value=mock_client):
            flush_traces()
            mock_client.flush.assert_called_once()
