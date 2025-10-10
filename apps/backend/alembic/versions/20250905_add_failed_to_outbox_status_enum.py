"""Add FAILED to outboxstatus enum

Revision ID: 20250905_add_failed
Revises: 3b8fe0c17290
Create Date: 2025-09-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250905_add_failed"
down_revision: Union[str, Sequence[str], None] = "3b8fe0c17290"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new value to existing PostgreSQL enum type
    op.execute("ALTER TYPE outboxstatus ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    # Note: Removing a value from a PostgreSQL enum type is non-trivial and unsafe;
    # downgrade is a no-op.
    pass

