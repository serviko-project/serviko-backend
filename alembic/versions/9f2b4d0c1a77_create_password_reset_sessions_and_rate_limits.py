"""create_password_reset_sessions_and_rate_limits

Revision ID: 9f2b4d0c1a77
Revises: 65ed963e87ff
Create Date: 2026-04-23 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b4d0c1a77"
down_revision: Union[str, None] = "65ed963e87ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_sessions",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_reset_sessions_email",
        "password_reset_sessions",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_sessions_expires_at",
        "password_reset_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_sessions_consumed_at",
        "password_reset_sessions",
        ["consumed_at"],
        unique=False,
    )

    op.create_table(
        "recovery_rate_limits",
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("last_request_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "endpoint",
            "email",
            "ip_address",
            name="uq_recovery_limit_scope",
        ),
    )
    op.create_index(
        "ix_recovery_rate_limits_email",
        "recovery_rate_limits",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_recovery_rate_limits_endpoint",
        "recovery_rate_limits",
        ["endpoint"],
        unique=False,
    )
    op.create_index(
        "ix_recovery_rate_limits_window_start",
        "recovery_rate_limits",
        ["window_start"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_recovery_rate_limits_window_start", table_name="recovery_rate_limits")
    op.drop_index("ix_recovery_rate_limits_endpoint", table_name="recovery_rate_limits")
    op.drop_index("ix_recovery_rate_limits_email", table_name="recovery_rate_limits")
    op.drop_table("recovery_rate_limits")

    op.drop_index("ix_password_reset_sessions_consumed_at", table_name="password_reset_sessions")
    op.drop_index("ix_password_reset_sessions_expires_at", table_name="password_reset_sessions")
    op.drop_index("ix_password_reset_sessions_email", table_name="password_reset_sessions")
    op.drop_table("password_reset_sessions")
