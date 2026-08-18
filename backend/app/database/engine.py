"""Async direct-Postgres engine for retrieval queries.

PostgREST (the supabase-py client) cannot express pgvector ``<=>`` operators
or Postgres full-text ranking, so retrieval runs raw SQL against the direct
``DATABASE_URL`` via SQLAlchemy's async engine. Process-wide singleton, mirroring
the Supabase client pattern in ``app/database/supabase.py``.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        # True async driver (asyncpg), so network I/O never blocks the event
        # loop. The sync psycopg dialect is kept for Alembic migrations.
        url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(url)
    return _engine
