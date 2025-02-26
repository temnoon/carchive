# alembic/versions/changes_to_media_table_and_more.py

"""Add Media Fields and Associations to Messages

Revision ID: <generated_revision_id>
Revises: <previous_revision_id>
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision = '<generated_revision_id>'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the media table for more comprehensive metadata
    op.add_column('media', sa.Column('message_id', sa.UUID(), nullable=True))  # ForeignKey to message
    op.add_column('media', sa.Column('linked_message_id', sa.UUID(), nullable=True))  # To associate media with another message (e.g., assistant or tool)

    # Optionally, add JSON column to store detailed metadata if required
    op.add_column('media', sa.Column('metadata', postgresql.JSONB, nullable=True))

    # Add the foreign key relationship from the media table to the messages table
    op.create_foreign_key('fk_media_message', 'media', 'messages', ['message_id'], ['id'])

    # If you need to create indexes on any frequently queried columns, you can add them as well
    op.create_index('ix_media_message_id', 'media', ['message_id'])


def downgrade():
    # Drop the foreign key and columns added
    op.drop_constraint('fk_media_message', 'media', type_='foreignkey')
    op.drop_column('media', 'message_id')
    op.drop_column('media', 'linked_message_id')
    op.drop_column('media', 'metadata')

    # Remove index if it was created
    op.drop_index('ix_media_message_id', 'media')
