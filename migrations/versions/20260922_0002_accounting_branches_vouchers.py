"""Add accounting branches and vouchers to an adopted baseline.

This revision is intentionally idempotent because the project's baseline
revision uses SQLAlchemy metadata.create_all() when bootstrapping a fresh DB.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260922_0002"
down_revision = "20260922_0001"
branch_labels = None
depends_on = None


def _columns(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "accounting_branches" not in tables:
        op.create_table(
            "accounting_branches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("name_ar", sa.String(length=180), nullable=False),
            sa.Column("phone", sa.String(length=40)),
            sa.Column("address_ar", sa.String(length=300)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_accounting_branches_code", "accounting_branches", ["code"], unique=False)

    journal_columns = _columns(bind, "journal_entries_v2")
    if "branch_id" not in journal_columns:
        op.add_column("journal_entries_v2", sa.Column("branch_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_journal_entries_v2_branch",
            "journal_entries_v2",
            "accounting_branches",
            ["branch_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    if "accounting_vouchers_v2" not in tables:
        op.create_table(
            "accounting_vouchers_v2",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("voucher_no", sa.String(length=60), nullable=False),
            sa.Column("voucher_type", sa.String(length=20), nullable=False),
            sa.Column("voucher_date", sa.Date(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("from_account_id", sa.Integer(), nullable=False),
            sa.Column("to_account_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Numeric(16, 2), nullable=False),
            sa.Column("reference", sa.String(length=180)),
            sa.Column("description_ar", sa.String(length=500), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="posted"),
            sa.Column("journal_entry_id", sa.Integer()),
            sa.Column("created_by_id", sa.Integer()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["branch_id"], ["accounting_branches.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["from_account_id"], ["accounts_v2.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["to_account_id"], ["accounts_v2.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries_v2.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.CheckConstraint("amount > 0", name="ck_accounting_voucher_amount_positive_v2"),
            sa.UniqueConstraint("voucher_no"),
        )
        op.create_index("ix_accounting_vouchers_v2_voucher_no", "accounting_vouchers_v2", ["voucher_no"], unique=False)


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "accounting_vouchers_v2" in tables:
        op.drop_table("accounting_vouchers_v2")
    journal_columns = _columns(bind, "journal_entries_v2")
    if "branch_id" in journal_columns:
        try:
            op.drop_constraint("fk_journal_entries_v2_branch", "journal_entries_v2", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("journal_entries_v2", "branch_id")
    if "accounting_branches" in tables:
        try:
            op.drop_index("ix_accounting_branches_code", table_name="accounting_branches")
        except Exception:
            pass
        op.drop_table("accounting_branches")
