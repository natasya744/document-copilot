"""Document chunk endpoints — surrounding context retrieval.

Requires a verified Supabase user. Wire format matches `frontend/src/lib/api.ts`.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_current_user
from app.retrieval.queries import fetch_surrounding

router = APIRouter(prefix="/chunks", tags=["chunks"])


class SurroundingChunkOut(BaseModel):
    chunkId: uuid.UUID
    documentId: uuid.UUID
    chunkIndex: int
    ticker: str
    companyName: str
    filingType: str
    filingDate: date
    year: int
    page: str | None = None
    section: str | None = None
    text: str


@router.get("/{chunk_id}/surrounding", response_model=list[SurroundingChunkOut])
async def get_surrounding_chunks(
    chunk_id: uuid.UUID,
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
    window: int = Query(default=1, ge=1, le=5),
) -> list[SurroundingChunkOut]:
    """Fetch preceding and succeeding chunks around ``chunk_id`` within the same filing."""
    passages = await fetch_surrounding(chunk_id, window=window)
    return [
        SurroundingChunkOut(
            chunkId=p.chunk_id,
            documentId=p.document_id,
            chunkIndex=p.chunk_index,
            ticker=p.ticker,
            companyName=p.company_name,
            filingType=p.filing_type,
            filingDate=p.filing_date,
            year=p.year,
            page=p.page,
            section=p.section,
            text=p.text,
        )
        for p in passages
    ]
