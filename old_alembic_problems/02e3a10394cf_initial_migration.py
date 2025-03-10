# File: alembic/versions/02e3a10394cf_initial_migration.py
"""Initial migration

Revision ID: 02e3a10394cf
Revises:
Create Date: 2025-01-28 22:41:42.519238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02e3a10394cf'
down_revision: Union[str, None] = None   # <-- set to None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_agent_outputs_output_type', table_name='agent_outputs')
    op.drop_index('idx_agent_outputs_target', table_name='agent_outputs')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_agent_outputs_target', 'agent_outputs', ['target_type', 'target_id'], unique=False)
    op.create_index('idx_agent_outputs_output_type', 'agent_outputs', ['output_type'], unique=False)
    # ### end Alembic commands ###
