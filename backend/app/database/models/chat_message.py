import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer)
    message_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index(
            "ix_chat_messages_thread_sequence",
            "thread_id",
            "sequence_number",
            unique=True,
        ),
    )