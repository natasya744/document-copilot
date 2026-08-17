import uuid
from datetime import date

from sqlalchemy import Date, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    filing_type: Mapped[str] = mapped_column(String(20), index=True)
    filing_date: Mapped[date] = mapped_column(Date)
    year: Mapped[int] = mapped_column(Integer, index=True)
    accession_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_url: Mapped[str] = mapped_column(Text)
    markdown_content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )

    __table_args__ = (Index("ix_source_documents_ticker_year", "ticker", "year"),)