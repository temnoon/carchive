"""Merge heads

Revision ID: merge_heads
Revises: add_collections_tables, add_media_enhanced_fields
Create Date: 2024-03-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('add_collections_tables', 'add_media_enhanced_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
