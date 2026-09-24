"""Configurable unpaid booking hold duration.

Revision ID: 20260924_0009
Revises: 20260924_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_0009"
down_revision = "20260924_0008"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("booking_policies")}
    if "hold_duration_minutes" not in columns:
        op.add_column(
            "booking_policies",
            sa.Column("hold_duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        )


def downgrade():
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("booking_policies")}
    if "hold_duration_minutes" in columns:
        op.drop_column("booking_policies", "hold_duration_minutes")
