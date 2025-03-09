"""add_media_type_column

Revision ID: a0845f5c5b98
Revises: c6bfc3795e47
Create Date: 2025-03-03 18:17:50.644863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0845f5c5b98'
down_revision: Union[str, None] = 'c6bfc3795e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the media_type column with a temporary nullable constraint
    op.add_column('media', sa.Column('media_type', sa.String(), nullable=True))
    
    # Update existing records - set a default value for existing media
    # First detect and set based on file extensions
    op.execute("""
    UPDATE media 
    SET media_type = 
        CASE 
            WHEN file_path LIKE '%.jpg' OR file_path LIKE '%.jpeg' OR file_path LIKE '%.png' 
                 OR file_path LIKE '%.gif' OR file_path LIKE '%.webp' OR file_path LIKE '%.avif' THEN 'image'
            WHEN file_path LIKE '%.mp3' OR file_path LIKE '%.wav' OR file_path LIKE '%.ogg' 
                 OR file_path LIKE '%.flac' THEN 'audio'
            WHEN file_path LIKE '%.mp4' OR file_path LIKE '%.mov' OR file_path LIKE '%.avi' 
                 OR file_path LIKE '%.webm' THEN 'video'
            WHEN file_path LIKE '%.pdf' THEN 'pdf'
            ELSE 'other'
        END
    WHERE media_type IS NULL
    """)
    
    # Set any remaining NULL values to 'other'
    op.execute("UPDATE media SET media_type = 'other' WHERE media_type IS NULL")
    
    # Now make the column non-nullable to match the model definition
    op.alter_column('media', 'media_type', nullable=False)


def downgrade() -> None:
    op.drop_column('media', 'media_type')
