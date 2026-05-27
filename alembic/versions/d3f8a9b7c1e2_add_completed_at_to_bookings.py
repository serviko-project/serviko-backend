"""Add completed_at and completion_note to bookings

Revision ID: d3f8a9b7c1e2
Revises: c7a4b2d91e53
Create Date: 2026-05-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "d3f8a9b7c1e2"
down_revision: Union[str, None] = "c7a4b2d91e53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("completion_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "completion_note")
    op.drop_column("bookings", "completed_at")
