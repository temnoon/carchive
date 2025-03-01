"""add_embedding_parent_columns

Revision ID: add_embedding_parent_columns
Revises: 
Create Date: 2025-02-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_embedding_parent_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add parent_message_id and parent_chunk_id columns to embeddings table
    op.add_column('embeddings', sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), 
                                          sa.ForeignKey('messages.id'), nullable=True))
    op.add_column('embeddings', sa.Column('parent_chunk_id', postgresql.UUID(as_uuid=True), 
                                          sa.ForeignKey('chunks.id'), nullable=True))
    
    # Create indexes for faster lookups
    op.create_index(op.f('ix_embeddings_parent_message_id'), 'embeddings', ['parent_message_id'], unique=False)
    op.create_index(op.f('ix_embeddings_parent_chunk_id'), 'embeddings', ['parent_chunk_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_embeddings_parent_chunk_id'), table_name='embeddings')
    op.drop_index(op.f('ix_embeddings_parent_message_id'), table_name='embeddings')
    
    # Drop columns
    op.drop_column('embeddings', 'parent_chunk_id')
    op.drop_column('embeddings', 'parent_message_id')