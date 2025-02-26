"""add media enhanced fields

Revision ID: add_media_enhanced_fields
Revises: 
Create Date: 2025-02-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'add_media_enhanced_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to media table
    op.add_column('media', sa.Column('original_file_id', sa.String(), nullable=True))
    op.add_column('media', sa.Column('file_name', sa.String(), nullable=True))
    op.add_column('media', sa.Column('source_url', sa.String(), nullable=True))
    op.add_column('media', sa.Column('is_generated', sa.Boolean(), server_default='false', nullable=False))
    
    # Create index on original_file_id for faster lookup
    op.create_index(op.f('ix_media_original_file_id'), 'media', ['original_file_id'], unique=False)


def downgrade():
    # Drop the new columns
    op.drop_index(op.f('ix_media_original_file_id'), table_name='media')
    op.drop_column('media', 'is_generated')
    op.drop_column('media', 'source_url')
    op.drop_column('media', 'file_name')
    op.drop_column('media', 'original_file_id')