"""update_genesis_stage_data_and_cleanup

Revision ID: d54f6b6e14e2
Revises: 909dc5666340
Create Date: 2025-09-05 23:11:41.666335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd54f6b6e14e2'
down_revision: Union[str, Sequence[str], None] = '909dc5666340'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update data and clean up old enum values."""
    # Update existing data - map old values to new values
    op.execute("UPDATE genesis_sessions SET current_stage = 'INITIAL_PROMPT' WHERE current_stage = 'CONCEPT_SELECTION'")
    op.execute("UPDATE genesis_sessions SET current_stage = 'INITIAL_PROMPT' WHERE current_stage = 'STORY_CONCEPTION'")
    
    # Update the constraint that references the enum values
    op.drop_constraint('check_genesis_stage_progression', 'genesis_sessions', type_='check')
    op.create_check_constraint(
        'check_genesis_stage_progression',
        'genesis_sessions',
        """
            (current_stage = 'INITIAL_PROMPT' AND status = 'IN_PROGRESS') OR
            (current_stage = 'WORLDVIEW' AND status = 'IN_PROGRESS') OR
            (current_stage = 'CHARACTERS' AND status = 'IN_PROGRESS') OR
            (current_stage = 'PLOT_OUTLINE' AND status = 'IN_PROGRESS') OR
            (current_stage = 'FINISHED' AND status IN ('COMPLETED', 'ABANDONED'))
        """
    )


def downgrade() -> None:
    """Downgrade - restore old enum values."""
    # Create old ENUM type
    old_genesisstage = sa.Enum(
        'CONCEPT_SELECTION', 'STORY_CONCEPTION', 'WORLDVIEW', 'CHARACTERS', 'PLOT_OUTLINE', 'FINISHED',
        name='genesisstage_old'
    )
    old_genesisstage.create(op.get_bind())
    
    # Update existing data - map new values back to old values
    op.execute("UPDATE genesis_sessions SET current_stage = 'CONCEPT_SELECTION' WHERE current_stage = 'INITIAL_PROMPT'")
    
    # Update the column to use the old enum type
    op.alter_column('genesis_sessions', 'current_stage',
                   type_=old_genesisstage,
                   postgresql_using='current_stage::text::genesisstage_old')
    
    # Drop the new enum type
    op.execute('DROP TYPE genesisstage')
    
    # Rename the old enum type back to the original name
    op.execute('ALTER TYPE genesisstage_old RENAME TO genesisstage')
    
    # Restore the old constraint
    op.drop_constraint('check_genesis_stage_progression', 'genesis_sessions', type_='check')
    op.create_check_constraint(
        'check_genesis_stage_progression',
        'genesis_sessions',
        """
            (current_stage = 'CONCEPT_SELECTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'STORY_CONCEPTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'WORLDVIEW' AND status = 'IN_PROGRESS') OR
            (current_stage = 'CHARACTERS' AND status = 'IN_PROGRESS') OR
            (current_stage = 'PLOT_OUTLINE' AND status = 'IN_PROGRESS') OR
            (current_stage = 'FINISHED' AND status IN ('COMPLETED', 'ABANDONED'))
        """
    )
