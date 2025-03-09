"""fix_media_enhanced_fields

Revision ID: ab7ad6ed5f84
Revises: a0845f5c5b98
Create Date: 2025-03-03 18:24:09.471683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab7ad6ed5f84'
down_revision: Union[str, None] = 'a0845f5c5b98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the columns from add_media_enhanced_fields.py - handle gracefully if they already exist
    try:
        op.add_column('media', sa.Column('original_file_id', sa.String(), nullable=True))
        op.add_column('media', sa.Column('file_name', sa.String(), nullable=True))
        op.add_column('media', sa.Column('source_url', sa.String(), nullable=True))
        op.add_column('media', sa.Column('is_generated', sa.Boolean(), server_default='false', nullable=False))
        
        # Create index on original_file_id for faster lookup
        op.create_index(op.f('ix_media_original_file_id'), 'media', ['original_file_id'], unique=False)
    except Exception as e:
        # If columns already exist or there's another issue, log it but continue
        print(f"Note: Could not add all columns, they may already exist: {str(e)}")


def downgrade() -> None:
    # Try to remove the columns but don't fail if they don't exist
    try:
        op.drop_index(op.f('ix_media_original_file_id'), table_name='media')
    except Exception:
        pass
        
    try:
        op.drop_column('media', 'is_generated')
    except Exception:
        pass
        
    try:
        op.drop_column('media', 'source_url')
    except Exception:
        pass
        
    try:
        op.drop_column('media', 'file_name')
    except Exception:
        pass
        
    try:
        op.drop_column('media', 'original_file_id')
    except Exception:
        pass
