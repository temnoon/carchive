"""add_saved_searches_table

Revision ID: a3267f8c5e98
Revises: edfd0f6d99c1
Create Date: 2025-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3267f8c5e98'
down_revision: Union[str, None] = 'edfd0f6d99c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create saved_searches table
    op.create_table('saved_searches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('query', sa.String(), nullable=False),
        sa.Column('search_type', sa.String(), nullable=False, server_default='all'),
        sa.Column('criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_saved_searches_name', 'saved_searches', ['name'], unique=False)
    op.create_index('idx_saved_searches_created_at', 'saved_searches', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop saved_searches table
    op.drop_index('idx_saved_searches_created_at', table_name='saved_searches')
    op.drop_index('idx_saved_searches_name', table_name='saved_searches')
    op.drop_table('saved_searches')