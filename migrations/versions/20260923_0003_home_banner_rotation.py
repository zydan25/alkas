"""Add configurable rotation duration to homepage announcement banners.

Revision ID: 20260923_0003
Revises: 20260922_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20260923_0003"
down_revision = "20260922_0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "announcement_cards" not in tables:
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns("announcement_cards")}
    if "rotation_seconds" not in columns:
        op.add_column(
            "announcement_cards",
            sa.Column("rotation_seconds", sa.Integer(), nullable=False, server_default=sa.text("6")),
        )
        op.alter_column("announcement_cards", "rotation_seconds", server_default=None)


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "announcement_cards" not in tables:
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns("announcement_cards")}
    if "rotation_seconds" in columns:
        op.drop_column("announcement_cards", "rotation_seconds")
