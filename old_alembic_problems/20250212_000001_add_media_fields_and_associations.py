# File: alembic/versions/20250212_000001_add_media_fields_and_associations.py
"""Add Media Fields and Associations to Messages

Revision ID: 20250212_000001
Revises: fd1958d03254
Create Date: 2025-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = '20250212_000001'
down_revision = 'fd1958d03254'  # Replace with your actual previous revision ID
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the media table for more comprehensive metadata
    op.add_column('media', sa.Column('message_id', sa.UUID(), nullable=True))  # ForeignKey to message
    op.add_column('media', sa.Column('linked_message_id', sa.UUID(), nullable=True))  # To associate media with another message (e.g., assistant or tool)

    # Optionally, add a JSONB column to store detailed metadata if required
    op.add_column('media', sa.Column('metadata', postgresql.JSONB, nullable=True))

    # Add the foreign key relationship from the media table to the messages table
    op.create_foreign_key('fk_media_message', 'media', 'messages', ['message_id'], ['id'])

    # Create an index on message_id if frequently queried
    op.create_index('ix_media_message_id', 'media', ['message_id'])


def downgrade():
    # Drop the foreign key and columns added in upgrade()
    op.drop_constraint('fk_media_message', 'media', type_='foreignkey')
    op.drop_index('ix_media_message_id', 'media')
    op.drop_column('media', 'message_id')
    op.drop_column('media', 'linked_message_id')
    op.drop_column('media', 'metadata')
