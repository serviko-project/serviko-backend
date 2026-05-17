"""add banner and per category pricing

Revision ID: a1b2c3d4e5f6
Revises: 73a748a29f0f
Create Date: 2026-05-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "b6e38735be07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "provider_profiles",
        sa.Column("banner_image_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "provider_services",
        sa.Column("base_price_per_hour", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("provider_services", "base_price_per_hour")
    op.drop_column("provider_profiles", "banner_image_url")
