"""remove_document_status_column

Revision ID: 73a748a29f0f
Revises: fcd691e84b94
Create Date: 2026-04-28 17:50:10.052299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73a748a29f0f'
down_revision: Union[str, None] = 'fcd691e84b94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('provider_documents', 'status')


def downgrade() -> None:
    op.add_column('provider_documents', sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=False, server_default='pending'))
