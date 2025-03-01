"""Add collections tables

Revision ID: add_collections_tables
Revises: add_embedding_parent_columns
Create Date: 2024-03-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'add_collections_tables'
down_revision = 'add_embedding_parent_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('meta_info', JSONB, nullable=True),
    )

    # Create collection_items table that matches the ORM model
    op.create_table(
        'collection_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE')),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('message_id', UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=True),
        sa.Column('chunk_id', UUID(as_uuid=True), sa.ForeignKey('chunks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('meta_info', JSONB, nullable=True),
    )

    # Create indexes
    op.create_index('idx_collection_items_collection', 'collection_items', ['collection_id'])
    op.create_index('idx_collection_items_conversation', 'collection_items', ['conversation_id'])
    op.create_index('idx_collection_items_message', 'collection_items', ['message_id'])
    op.create_index('idx_collection_items_chunk', 'collection_items', ['chunk_id'])


def downgrade():
    op.drop_index('idx_collection_items_chunk', 'collection_items')
    op.drop_index('idx_collection_items_message', 'collection_items')
    op.drop_index('idx_collection_items_conversation', 'collection_items')
    op.drop_index('idx_collection_items_collection', 'collection_items')
    op.drop_table('collection_items')
    op.drop_table('collections')
