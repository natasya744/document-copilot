"""create auth user profile trigger

Revision ID: 91584bc0c7e4
Revises: c5aad791929d
Create Date: 2026-08-16 20:12:57.639356

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91584bc0c7e4"
down_revision: str | Sequence[str] | None = "c5aad791929d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Mirror every Supabase auth user into `public.users` so chat_threads FK
    # constraints hold for accounts created via the dashboard or the admin API.
    # SECURITY DEFINER runs as postgres, bypassing the `users` RLS policy.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER SET search_path = public
        AS $$
        BEGIN
            INSERT INTO public.users (id, email, display_name)
            VALUES (
                NEW.id,
                NEW.email,
                NEW.raw_user_meta_data->>'full_name'
            )
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_user()
        """
    )

    # Backfill rows for auth users that existed before this trigger.
    op.execute(
        """
        INSERT INTO public.users (id, email)
        SELECT id, email FROM auth.users
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user()")
