import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.assistant.outputs import SourcePassage
from app.auth.dependencies import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CHUNK_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DOC_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def authed() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=USER_ID, email="a@b.com"
    )
    yield
    app.dependency_overrides.clear()


def test_surrounding_chunks_requires_auth() -> None:
    response = client.get(f"/chunks/{CHUNK_ID}/surrounding")
    assert response.status_code == 401


def test_surrounding_chunks_success(authed: None) -> None:
    sample_passage = SourcePassage(
        chunk_id=CHUNK_ID,
        document_id=DOC_ID,
        chunk_index=42,
        ticker="MSFT",
        company_name="Microsoft Corporation",
        filing_type="10-K",
        filing_date=date(2021, 7, 29),
        year=2021,
        page="22",
        section="Item 1A",
        text="Sample passage text",
    )

    with patch("app.api.chunks.fetch_surrounding", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [sample_passage]
        response = client.get(f"/chunks/{CHUNK_ID}/surrounding?window=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["chunkId"] == str(CHUNK_ID)
    assert data[0]["ticker"] == "MSFT"
    assert data[0]["chunkIndex"] == 42
    assert data[0]["text"] == "Sample passage text"
