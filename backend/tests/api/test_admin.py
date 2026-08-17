from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.main import app

client = TestClient(app)


class FakeUser:
    def __init__(self, user_id: str, email: str) -> None:
        self.id = user_id
        self.email = email


class FakeUserResponse:
    user: FakeUser


class FakeAdmin:
    def __init__(self, response=None, *, error=None) -> None:
        self._response = response
        self._error = error

    async def create_user(self, attributes):
        if self._error is not None:
            raise self._error
        return self._response


class FakeAuth:
    def __init__(self, admin: FakeAdmin) -> None:
        self.admin = admin


class FakeClient:
    def __init__(self, auth: FakeAuth) -> None:
        self.auth = auth


def _patch_client(fake: FakeClient):
    get_client = AsyncMock(return_value=fake)
    return patch("app.api.admin.get_async_admin_client", get_client)


def _payload():
    return {"email": "analyst@driftwoodcapital.com", "password": "supersecret"}


def test_create_user_requires_admin_key():
    response = client.post("/admin/users", json=_payload())
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid admin key"}


def test_create_user_rejects_wrong_key():
    response = client.post(
        "/admin/users",
        json=_payload(),
        headers={"X-Admin-Key": "nope"},
    )
    assert response.status_code == 401


def test_create_user_success():
    created = FakeUserResponse()
    created.user = FakeUser("11111111-1111-1111-1111-111111111111", _payload()["email"])
    fake = FakeClient(FakeAuth(FakeAdmin(created)))
    with _patch_client(fake):
        response = client.post(
            "/admin/users",
            json=_payload(),
            headers={"X-Admin-Key": settings.admin_api_key},
        )
    assert response.status_code == 201
    assert response.json() == {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": _payload()["email"],
    }


def test_create_user_already_registered_is_409():
    fake = FakeClient(
        FakeAuth(FakeAdmin(error=AuthApiError("User already registered", 422, None)))
    )
    with _patch_client(fake):
        response = client.post(
            "/admin/users",
            json=_payload(),
            headers={"X-Admin-Key": settings.admin_api_key},
        )
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


def test_create_user_supabase_error_is_502():
    fake = FakeClient(
        FakeAuth(FakeAdmin(error=AuthApiError("Internal server error", 500, None)))
    )
    with _patch_client(fake):
        response = client.post(
            "/admin/users",
            json=_payload(),
            headers={"X-Admin-Key": settings.admin_api_key},
        )
    assert response.status_code == 502


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "supersecret"},
        {"password": "supersecret"},
        {"email": "analyst@driftwoodcapital.com"},
        {"email": "analyst@driftwoodcapital.com", "password": "short"},
    ],
)
def test_create_user_validates_payload(payload):
    response = client.post(
        "/admin/users",
        json=payload,
        headers={"X-Admin-Key": settings.admin_api_key},
    )
    assert response.status_code == 422
