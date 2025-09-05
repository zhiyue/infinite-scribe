"""add user_id to novels table

Revision ID: d26625f6db43
Revises: fdf4baeb26a6
Create Date: 2025-09-05 20:19:21.056004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd26625f6db43'
down_revision: Union[str, Sequence[str], None] = 'fdf4baeb26a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column to novels table
    op.add_column('novels', sa.Column('user_id', sa.Integer(), nullable=False, comment='所属用户ID，外键关联users表'))
    
    # Create foreign key constraint to users table
    op.create_foreign_key(
        'fk_novels_user_id',  # constraint name
        'novels',             # source table
        'users',              # target table
        ['user_id'],          # source column
        ['id'],               # target column
        ondelete='CASCADE'    # delete novels when user is deleted
    )
    
    # Create index on user_id for performance
    op.create_index('idx_novels_user_id', 'novels', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('idx_novels_user_id', table_name='novels')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_novels_user_id', 'novels', type_='foreignkey')
    
    # Drop user_id column
    op.drop_column('novels', 'user_id')
