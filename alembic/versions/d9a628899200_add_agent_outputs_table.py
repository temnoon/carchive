"""add_agent_outputs_table

Revision ID: d9a628899200
Revises: merge_heads
Create Date: 2025-03-01 11:17:01.197242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9a628899200'
down_revision: Union[str, None] = 'merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_outputs table
    op.create_table(
        'agent_outputs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('output_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for faster lookups
    op.create_index('idx_agent_outputs_target', 'agent_outputs', ['target_type', 'target_id', 'output_type'], unique=False)
    op.create_index('idx_agent_outputs_type', 'agent_outputs', ['output_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_agent_outputs_target', table_name='agent_outputs')
    op.drop_index('idx_agent_outputs_type', table_name='agent_outputs')
    
    # Drop table
    op.drop_table('agent_outputs')
