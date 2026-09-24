"""Track remaining players in multi-player bookings.

Revision ID: 20260924_0010
Revises: 20260924_0009
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_0010"
down_revision = "20260924_0009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("bookings")}
    if "participant_count" not in columns:
        op.add_column("bookings", sa.Column("participant_count", sa.Integer(), nullable=True))
    if "participants_remaining" not in columns:
        op.add_column("bookings", sa.Column("participants_remaining", sa.Integer(), nullable=True))
    if "participant_unit_price" not in columns:
        op.add_column("bookings", sa.Column("participant_unit_price", sa.Numeric(14, 2), nullable=True))


def downgrade():
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("bookings")}
    if "participant_unit_price" in columns:
        op.drop_column("bookings", "participant_unit_price")
    if "participants_remaining" in columns:
        op.drop_column("bookings", "participants_remaining")
    if "participant_count" in columns:
        op.drop_column("bookings", "participant_count")
