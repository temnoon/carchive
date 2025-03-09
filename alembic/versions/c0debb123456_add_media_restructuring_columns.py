"""Add media restructuring columns

Revision ID: c0debb123456
Revises: ab7ad6ed5f84
Create Date: 2025-03-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'c0debb123456'
down_revision = 'ab7ad6ed5f84'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the media table
    op.add_column('media', sa.Column('archive_source', sa.String(), nullable=True))
    op.add_column('media', sa.Column('relative_path', sa.String(), nullable=True))
    op.add_column('media', sa.Column('original_path', sa.String(), nullable=True))
    
    # Create new indexes - wrapped in try/except to handle case where indexes already exist
    try:
        op.create_index('ix_media_original_file_id', 'media', ['original_file_id'], unique=False)
    except Exception as e:
        print(f"Index ix_media_original_file_id creation skipped: {e}")
    
    try:
        op.create_index('ix_media_checksum', 'media', ['checksum'], unique=False)
    except Exception as e:
        print(f"Index ix_media_checksum creation skipped: {e}")


def downgrade():
    # Remove new columns from the media table
    op.drop_column('media', 'archive_source')
    op.drop_column('media', 'relative_path')
    op.drop_column('media', 'original_path')
    
    # Drop indexes
    op.drop_index('ix_media_original_file_id', table_name='media')
    op.drop_index('ix_media_checksum', table_name='media')