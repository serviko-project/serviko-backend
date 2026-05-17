"""add proposed_base_price to category_requests

Revision ID: 390a0776aae5
Revises: 292fdfe8a08b
Create Date: 2026-05-16 19:52:18.002975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '390a0776aae5'
down_revision: Union[str, None] = '292fdfe8a08b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('category_requests', sa.Column('proposed_base_price', sa.Float(), server_default='0.0', nullable=False))


def downgrade() -> None:
    op.drop_column('category_requests', 'proposed_base_price')
