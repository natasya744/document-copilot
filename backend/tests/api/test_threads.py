import uuid
from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
THREAD_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_THREAD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
MESSAGE_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

TIMESTAMP = "2026-08-16T10:00:00Z"


@pytest.fixture
def authed() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=USER_ID, email="a@b.com"
    )
    yield
    app.dependency_overrides.clear()


def _thread_row(
    *, thread_id: uuid.UUID = THREAD_ID, owner: uuid.UUID = USER_ID
) -> dict:
    return {
        "id": str(thread_id),
        "user_id": str(owner),
        "title": "New chat",
        "created_at": TIMESTAMP,
        "updated_at": TIMESTAMP,
        "first_message": "First user question here",
    }


def _message_row(
    *,
    thread_id: uuid.UUID = THREAD_ID,
    message_json: dict | None = None,
) -> dict:
    return {
        "id": str(MESSAGE_ID),
        "thread_id": str(thread_id),
        "role": "user",
        "content": "hello",
        "sequence_number": 1,
        "created_at": TIMESTAMP,
        "message_json": message_json,
    }


def _patch_chats(name: str, return_value):
    return patch(f"app.database.chats.{name}", new=AsyncMock(return_value=return_value))


def _expected_thread(*, thread_id: uuid.UUID = THREAD_ID) -> dict:
    return {
        "id": str(thread_id),
        "title": "New chat",
        "createdAt": TIMESTAMP,
        "updatedAt": TIMESTAMP,
        "firstMessage": "First user question here",
    }


def _expected_message(*, thread_id: uuid.UUID = THREAD_ID) -> dict:
    return {
        "id": str(MESSAGE_ID),
        "threadId": str(thread_id),
        "role": "user",
        "content": "hello",
        "sequenceNumber": 1,
        "createdAt": TIMESTAMP,
        "parts": None,
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/threads"),
        ("post", "/threads"),
        ("get", f"/threads/{THREAD_ID}"),
        ("get", f"/threads/{THREAD_ID}/messages"),
        ("delete", f"/threads/{THREAD_ID}"),
    ],
)
def test_thread_endpoints_require_auth(method, path):
    response = client.request(method, path)
    assert response.status_code == 401


def test_list_threads_returns_users_threads(authed):
    rows = [
        _thread_row(),
        _thread_row(thread_id=OTHER_THREAD_ID),
    ]
    with (
        _patch_chats("purge_stale_empty_threads", None),
        _patch_chats("list_threads", rows) as mock_list,
    ):
        response = client.get("/threads")
    assert response.status_code == 200
    assert response.json() == [
        _expected_thread(),
        _expected_thread(thread_id=OTHER_THREAD_ID),
    ]
    mock_list.assert_awaited_once_with(ANY, USER_ID)


def test_list_threads_purges_stale_empty_threads(authed):
    with (
        _patch_chats("purge_stale_empty_threads", None) as mock_purge,
        _patch_chats("list_threads", []),
    ):
        response = client.get("/threads")
    assert response.status_code == 200
    assert response.json() == []
    mock_purge.assert_awaited_once_with(ANY, USER_ID)


def test_create_thread_success(authed):
    with _patch_chats("create_thread", _thread_row()) as mock_create:
        response = client.post("/threads", json={"title": "New chat"})
    assert response.status_code == 201
    assert response.json() == _expected_thread()
    mock_create.assert_awaited_once_with(ANY, user_id=USER_ID, title="New chat")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "x" * 256},
        {"title": "ok", "extra": "nope"},
    ],
)
def test_create_thread_validates_payload(authed, payload):
    response = client.post("/threads", json=payload)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_get_thread_success(authed):
    with _patch_chats("get_thread", _thread_row()):
        response = client.get(f"/threads/{THREAD_ID}")
    assert response.status_code == 200
    assert response.json() == _expected_thread()


def test_get_thread_missing_is_404(authed):
    with _patch_chats("get_thread", None):
        response = client.get(f"/threads/{THREAD_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Thread not found"}


def test_get_another_users_thread_is_403(authed):
    with _patch_chats("get_thread", _thread_row(owner=OTHER_USER_ID)):
        response = client.get(f"/threads/{THREAD_ID}")
    assert response.status_code == 403
    assert response.json() == {"detail": "You do not have access to this resource"}


def test_list_messages_success(authed):
    with (
        _patch_chats("get_thread", _thread_row()),
        _patch_chats("list_messages", [_message_row()]),
    ):
        response = client.get(f"/threads/{THREAD_ID}/messages")
    assert response.status_code == 200
    assert response.json() == [_expected_message()]


def test_list_messages_rehydrates_persisted_parts(authed):
    message_json = {
        "role": "assistant",
        "parts": [
            {"type": "text", "text": "Grounded answer."},
            {
                "type": "data-citations",
                "data": {"citations": [{"ticker": "NVDA", "excerpt": "passage"}]},
            },
        ],
    }
    row = _message_row(message_json=message_json)
    row["role"] = "assistant"
    with (
        _patch_chats("get_thread", _thread_row()),
        _patch_chats("list_messages", [row]),
    ):
        response = client.get(f"/threads/{THREAD_ID}/messages")
    assert response.status_code == 200
    body = response.json()[0]
    assert body["role"] == "assistant"
    assert body["parts"] == message_json["parts"]
    assert body["parts"][1]["type"] == "data-citations"


def test_list_messages_missing_thread_is_404(authed):
    with _patch_chats("get_thread", None):
        response = client.get(f"/threads/{THREAD_ID}/messages")
    assert response.status_code == 404
    assert response.json() == {"detail": "Thread not found"}


def test_list_messages_foreign_thread_is_403(authed):
    with _patch_chats("get_thread", _thread_row(owner=OTHER_USER_ID)):
        response = client.get(f"/threads/{THREAD_ID}/messages")
    assert response.status_code == 403


def test_malformed_thread_id_is_422(authed):
    response = client.get("/threads/not-a-uuid")
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_unhandled_error_is_500_json():
    client_no_raise = TestClient(app, raise_server_exceptions=False)

    def boom():
        raise RuntimeError("boom")

    app.dependency_overrides[get_current_user] = boom
    try:
        response = client_no_raise.get("/threads")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_delete_thread_success(authed):
    with _patch_chats("get_thread", _thread_row()):
        response = client.delete(f"/threads/{THREAD_ID}")
    assert response.status_code == 204


def test_delete_thread_missing_is_404(authed):
    with _patch_chats("get_thread", None):
        response = client.delete(f"/threads/{THREAD_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Thread not found"}


def test_delete_thread_foreign_is_403(authed):
    with _patch_chats("get_thread", _thread_row(owner=OTHER_USER_ID)):
        response = client.delete(f"/threads/{THREAD_ID}")
    assert response.status_code == 403
    assert response.json() == {"detail": "You do not have access to this resource"}


def test_delete_malformed_thread_id_is_422(authed):
    response = client.delete("/threads/not-a-uuid")
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
