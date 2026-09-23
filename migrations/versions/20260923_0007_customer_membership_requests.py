"""Customer membership applications/subscriptions and private chat.

Revision ID: 20260923_0007
Revises: 20260923_0006
"""
from alembic import op
import sqlalchemy as sa

revision="20260923_0007"
down_revision="20260923_0006"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "membership_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title_ar", sa.String(length=180), nullable=False),
        sa.Column("price", sa.Numeric(16,2), nullable=False, server_default="0"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("starts_on", sa.Date()),
        sa.Column("ends_on", sa.Date()),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("cancellation_reason", sa.String(length=700)),
        sa.Column("admin_note", sa.String(length=700)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_membership_requests_customer_id","membership_requests",["customer_id"])
    op.create_index("ix_membership_requests_status","membership_requests",["status"])

    op.create_table(
        "membership_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("membership_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sender_role", sa.String(length=30), nullable=False, server_default="customer"),
        sa.Column("body_ar", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_membership_messages_request_id","membership_messages",["request_id"])

def downgrade():
    op.drop_index("ix_membership_messages_request_id", table_name="membership_messages")
    op.drop_table("membership_messages")
    op.drop_index("ix_membership_requests_status", table_name="membership_requests")
    op.drop_index("ix_membership_requests_customer_id", table_name="membership_requests")
    op.drop_table("membership_requests")
