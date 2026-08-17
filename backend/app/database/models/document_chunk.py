import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    page: Mapped[str | None] = mapped_column(String(64))
    section: Mapped[str | None] = mapped_column(String(255))
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[object | None] = mapped_column(Vector(1536))
    search_vector: Mapped[object | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', chunk_text)", persisted=True),
    )
    token_count: Mapped[int] = mapped_column(Integer)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_document_chunks_document_index",
            "document_id",
            "chunk_index",
            unique=True,
        ),
    )