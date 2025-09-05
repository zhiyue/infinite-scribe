"""merge migration branches

Revision ID: fdf4baeb26a6
Revises: 20250905_add_failed, 9de0f061b66e
Create Date: 2025-09-05 20:13:35.345525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdf4baeb26a6'
down_revision: Union[str, Sequence[str], None] = ('20250905_add_failed', '9de0f061b66e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
