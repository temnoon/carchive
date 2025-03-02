"""Add results buffer system tables

Revision ID: edfd0f6d99c1
Revises: d9a628899200
Create Date: 2025-03-02 13:35:49.362446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'edfd0f6d99c1'
down_revision: Union[str, None] = 'd9a628899200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create results_buffers table
    op.create_table(
        'results_buffers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('buffer_type', sa.String(), nullable=False, server_default='session'),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('meta_info', JSONB(), nullable=True),
        sa.UniqueConstraint('name', 'session_id', name='unique_buffer_name_per_session')
    )

    # Create buffer_items table 
    op.create_table(
        'buffer_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('buffer_id', UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', UUID(as_uuid=True), nullable=True),
        sa.Column('chunk_id', UUID(as_uuid=True), nullable=True),
        sa.Column('gencom_id', UUID(as_uuid=True), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta_info', JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['buffer_id'], ['results_buffers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id']),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id']),
        sa.ForeignKeyConstraint(['gencom_id'], ['agent_outputs.id'])
    )

    # Create indexes
    op.create_index('idx_buffer_items_buffer_id', 'buffer_items', ['buffer_id'])
    op.create_index('idx_buffer_items_message_id', 'buffer_items', ['message_id'])
    op.create_index('idx_buffer_items_conversation_id', 'buffer_items', ['conversation_id'])
    op.create_index('idx_buffer_items_chunk_id', 'buffer_items', ['chunk_id'])
    op.create_index('idx_buffer_items_gencom_id', 'buffer_items', ['gencom_id'])
    op.create_index('idx_buffer_items_position', 'buffer_items', ['position'])
    op.create_index('idx_results_buffers_name', 'results_buffers', ['name'])
    op.create_index('idx_results_buffers_session_id', 'results_buffers', ['session_id'])
    op.create_index('idx_results_buffers_buffer_type', 'results_buffers', ['buffer_type'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('buffer_items')
    op.drop_table('results_buffers')
