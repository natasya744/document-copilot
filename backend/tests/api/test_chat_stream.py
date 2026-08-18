import uuid
from contextlib import ExitStack, contextmanager
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
THREAD_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CHUNK_1 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
ASSISTANT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

TIMESTAMP = "2026-08-16T10:00:00Z"


class FakeRetriever:
    def __init__(self, passages):
        self.passages = passages

    async def retrieve(self, query):
        return self.passages


class FakeAgent:
    def __init__(self, answer):
        self.answer = answer

    async def generate(self, conversation, passages):
        return self.answer, passages


def _thread_row(*, owner: uuid.UUID = USER_ID) -> dict:
    return {
        "id": str(THREAD_ID),
        "user_id": str(owner),
        "title": "New chat",
        "created_at": TIMESTAMP,
        "updated_at": TIMESTAMP,
    }


def _passage() -> SourcePassage:
    return SourcePassage(
        chunk_id=CHUNK_1,
        document_id=DOCUMENT_ID,
        chunk_index=0,
        ticker="NVDA",
        company_name="NVIDIA Corp",
        filing_type="10-K",
        filing_date=date(2025, 1, 31),
        year=2025,
        page="p. 10",
        section="Risk Factors",
        text="Retrieved passage text.",
    )


def _assistant_row():
    return {"id": str(ASSISTANT_ID), "sequence_number": 2}


@pytest.fixture
def authed():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=USER_ID, email="a@b.com"
    )
    yield
    app.dependency_overrides.clear()


def _stream_payload(*, thread_id: uuid.UUID = THREAD_ID) -> dict:
    return {
        "threadId": str(thread_id),
        "messages": [
            {"id": "m1", "role": "user", "parts": [{"type": "text", "text": "hello"}]}
        ],
        "id": "chat-1",
        "trigger": "submit",
        "messageId": "m1",
    }


def _patch_factories(*, retriever=None, agent=None):
    patches = []
    if retriever is not None:
        patches.append(patch("app.api.chat_stream.default_retriever", lambda: retriever))
    if agent is not None:
        patches.append(
            patch("app.api.chat_stream.default_agent", lambda retriever=None: agent)
        )
    return patches


def _patch_persistence(*, retriever=None, agent=None):
    return (
        patch("app.api.chat.chats.get_thread", AsyncMock(return_value=_thread_row())),
        patch("app.api.chat_stream.chats.list_messages", AsyncMock(return_value=[])),
        patch(
            "app.chat.orchestrator.chats.create_message",
            AsyncMock(return_value=_assistant_row()),
        ),
        patch(
            "app.chat.orchestrator.chats.create_citation",
            AsyncMock(return_value={}),
        ),
        *_patch_factories(retriever=retriever, agent=agent),
    )


def _read_events(response) -> list[dict]:
    import json

    lines = response.read().decode().splitlines()
    return [json.loads(line[len("data: ") :]) for line in lines if line.strip()]


@contextmanager
def _stream_session(payload, *, retriever=None, agent=None):
    """Stream a request with persistence mocked; yields the response."""
    with ExitStack() as stack:
        for cm in _patch_persistence(retriever=retriever, agent=agent):
            stack.enter_context(cm)
        response = stack.enter_context(client.stream("POST", "/chat/stream", json=payload))
        yield response


def test_stream_requires_auth():
    response = client.post("/chat/stream", json=_stream_payload())
    assert response.status_code == 401


def test_stream_missing_thread_is_404(authed):
    with patch("app.api.chat.chats.get_thread", AsyncMock(return_value=None)):
        response = client.post("/chat/stream", json=_stream_payload())
    assert response.status_code == 404


def test_stream_foreign_thread_is_403(authed):
    with patch(
        "app.api.chat.chats.get_thread",
        AsyncMock(return_value=_thread_row(owner=OTHER_USER_ID)),
    ):
        response = client.post("/chat/stream", json=_stream_payload())
    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"threadId": "not-a-uuid", "messages": []},
        {"threadId": str(THREAD_ID)},
        {"threadId": str(THREAD_ID), "messages": "nope"},
    ],
)
def test_stream_validates_payload(authed, payload):
    response = client.post("/chat/stream", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_stream_success(authed):
    agent = FakeAgent(
        GroundedAnswer(answer="Grounded answer.", citations=(Citation.from_passage(_passage()),))
    )
    with _stream_session(
        _stream_payload(), retriever=FakeRetriever([_passage()]), agent=agent
    ) as response:
        assert response.status_code == 200
        events = _read_events(response)

    assert events[0]["type"] == "start"
    assert events[0]["messageId"] == str(ASSISTANT_ID)
    assert events[-1]["type"] == "finish"
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert "".join(deltas) == "Grounded answer."
    citations = next(e for e in events if e["type"] == "data-citations")
    assert citations["data"]["citations"][0]["ticker"] == "NVDA"


def test_stream_grounding_failure_returns_error_event(authed):
    agent = FakeAgent(GroundedAnswer(answer="Bad answer."))
    with _stream_session(
        _stream_payload(), retriever=FakeRetriever([]), agent=agent
    ) as response:
        assert response.status_code == 200
        events = _read_events(response)

    assert events == [{"type": "error", "errorText": "Answer has no citations"}]