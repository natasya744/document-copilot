"""add_get_threads_with_first_message_function

Revision ID: df84319c36d5
Revises: 91584bc0c7e4
Create Date: 2026-08-22 12:28:44.236144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df84319c36d5'
down_revision: Union[str, Sequence[str], None] = '91584bc0c7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE OR REPLACE FUNCTION get_threads_with_first_message(p_user_id uuid)
        RETURNS TABLE (
            id uuid,
            user_id uuid,
            title text,
            created_at timestamptz,
            updated_at timestamptz,
            first_message text
        ) LANGUAGE sql STABLE AS $$
            SELECT
                t.id,
                t.user_id,
                t.title,
                t.created_at,
                t.updated_at,
                m.content as first_message
            FROM chat_threads t
            LEFT JOIN LATERAL (
                SELECT content
                FROM chat_messages cm
                WHERE cm.thread_id = t.id
                  AND cm.role = 'user'
                ORDER BY cm.sequence_number ASC
                LIMIT 1
            ) m ON true
            WHERE t.user_id = p_user_id
            ORDER BY t.updated_at DESC;
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS get_threads_with_first_message(uuid);")
