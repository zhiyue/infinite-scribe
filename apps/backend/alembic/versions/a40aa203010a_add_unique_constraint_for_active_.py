"""add_unique_constraint_for_active_sessions

Revision ID: a40aa203010a
Revises: d54f6b6e14e2
Create Date: 2025-09-09 23:04:00.770682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a40aa203010a'
down_revision: Union[str, Sequence[str], None] = 'd54f6b6e14e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add partial unique index to ensure only one active session per scope
    # This allows multiple inactive sessions for the same scope but only one active
    op.execute("""
        CREATE UNIQUE INDEX 
        uq_conversation_sessions_active_per_scope 
        ON conversation_sessions (scope_type, scope_id) 
        WHERE status = 'ACTIVE'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the partial unique index
    op.execute("DROP INDEX IF EXISTS uq_conversation_sessions_active_per_scope")
