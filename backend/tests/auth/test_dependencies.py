import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError

from app.auth.dependencies import CurrentUser, get_current_user


class FakeCredentials:
    def __init__(self, token: str = "TOK") -> None:
        self.credentials = token


class FakeUser:
    id = str(uuid.uuid4())
    email = "a@b.com"


class FakeResponse:
    user = FakeUser()


def _client_with(response=None, *, error=None):
    client = AsyncMock()
    if error is not None:
        client.get_user = AsyncMock(side_effect=error)
    else:
        client.get_user = AsyncMock(return_value=response)
    return client


async def test_missing_token_is_401():
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(None)
    assert excinfo.value.status_code == 401


async def test_invalid_token_is_401():
    client = _client_with(error=AuthApiError("bad token", 401, None))
    with (
        patch("app.auth.dependencies._get_auth_client", return_value=client),
        pytest.raises(HTTPException) as excinfo,
    ):
        await get_current_user(FakeCredentials())
    assert excinfo.value.status_code == 401


async def test_empty_response_is_401():
    client = _client_with(response=None)
    with (
        patch("app.auth.dependencies._get_auth_client", return_value=client),
        pytest.raises(HTTPException) as excinfo,
    ):
        await get_current_user(FakeCredentials())
    assert excinfo.value.status_code == 401


async def test_valid_token_returns_current_user():
    client = _client_with(response=FakeResponse())
    with patch("app.auth.dependencies._get_auth_client", return_value=client):
        user = await get_current_user(FakeCredentials())
    assert isinstance(user, CurrentUser)
    assert str(user.id) == FakeUser.id
    assert user.email == "a@b.com"
