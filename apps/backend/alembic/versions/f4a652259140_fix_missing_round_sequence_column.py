"""fix missing round_sequence column

Revision ID: f4a652259140
Revises: a40aa203010a
Create Date: 2025-09-10 23:44:27.311158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a652259140'
down_revision: Union[str, Sequence[str], None] = 'a40aa203010a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing round_sequence column to conversation_sessions if it doesn't exist."""
    # Check if column exists first, then add if missing
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'conversation_sessions' 
                AND column_name = 'round_sequence'
            ) THEN
                ALTER TABLE conversation_sessions 
                ADD COLUMN round_sequence INTEGER NOT NULL DEFAULT 0;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove round_sequence column if it exists."""
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'conversation_sessions' 
                AND column_name = 'round_sequence'
            ) THEN
                ALTER TABLE conversation_sessions 
                DROP COLUMN round_sequence;
            END IF;
        END $$;
    """)
