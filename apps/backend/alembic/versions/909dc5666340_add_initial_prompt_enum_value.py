"""add_initial_prompt_enum_value

Revision ID: 909dc5666340
Revises: d26625f6db43
Create Date: 2025-09-05 23:10:49.058054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '909dc5666340'
down_revision: Union[str, Sequence[str], None] = 'd26625f6db43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the new INITIAL_PROMPT enum value."""
    # Add new enum value
    op.execute("ALTER TYPE genesisstage ADD VALUE 'INITIAL_PROMPT'")


def downgrade() -> None:
    """Remove the INITIAL_PROMPT enum value."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, but for simplicity we'll leave it
    pass
