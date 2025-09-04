"""Add conversation tables with constraints and indexes for ADR-001

Revision ID: 9de0f061b66e
Revises: 06127b2a2f28
Create Date: 2025-09-05 05:49:48.125599

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9de0f061b66e'
down_revision: Union[str, Sequence[str], None] = '06127b2a2f28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversation_sessions table with constraints and indexes
    op.create_table(
        'conversation_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope_type', sa.String(32), nullable=False),
        sa.Column('scope_id', sa.Text(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column('stage', sa.String(64), nullable=True),
        sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for conversation_sessions
    op.create_index('idx_conversation_sessions_scope', 'conversation_sessions', ['scope_type', 'scope_id'])
    op.create_index('idx_conversation_sessions_status', 'conversation_sessions', ['status'])
    op.create_index('idx_conversation_sessions_updated_at', 'conversation_sessions', ['updated_at'])
    op.create_index('idx_conversation_sessions_scope_status', 'conversation_sessions', ['scope_type', 'scope_id', 'status'])

    # Create conversation_rounds table with constraints and indexes
    op.create_table(
        'conversation_rounds',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('round_path', sa.String(64), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model', sa.String(128), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Numeric(10, 4), nullable=True),
        sa.Column('correlation_id', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('session_id', 'round_path'),
        sa.ForeignKeyConstraint(['session_id'], ['conversation_sessions.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for conversation_rounds
    op.create_index('idx_conversation_rounds_session_id', 'conversation_rounds', ['session_id'])
    op.create_index('idx_conversation_rounds_correlation_id', 'conversation_rounds', ['correlation_id'])
    op.create_index('idx_conversation_rounds_created_at', 'conversation_rounds', ['created_at'])
    op.create_index('idx_conversation_rounds_role', 'conversation_rounds', ['role'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (respect foreign key constraints)
    op.drop_table('conversation_rounds')
    op.drop_table('conversation_sessions')
