from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index

from ..extensions import db


class Branch(db.Model):
    __tablename__ = "accounting_branches"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(180), nullable=False)
    phone = db.Column(db.String(40))
    address_ar = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Account(db.Model):
    __tablename__ = "accounts_v2"
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("accounts_v2.id", ondelete="RESTRICT"))
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(180), nullable=False)
    account_type = db.Column(db.String(40), nullable=False)
    is_control = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    parent = db.relationship("Account", remote_side=[id], backref=db.backref("children", lazy="selectin"))

    @property
    def is_postable(self):
        return bool(self.is_active and not self.is_control and not self.children)

    @property
    def is_parent(self):
        return bool(self.children)


class CostCenter(db.Model):
    __tablename__ = "cost_centers"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name_ar = db.Column(db.String(180), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class FiscalPeriod(db.Model):
    __tablename__ = "fiscal_periods"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    closed_at = db.Column(db.DateTime(timezone=True))


class JournalEntry(db.Model):
    __tablename__ = "journal_entries_v2"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    entry_date = db.Column(db.Date, nullable=False)
    description_ar = db.Column(db.String(500), nullable=False)
    reference_type = db.Column(db.String(80))
    reference_id = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default="draft")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    branch_id = db.Column(db.Integer, db.ForeignKey("accounting_branches.id", ondelete="RESTRICT"))
    posted_at = db.Column(db.DateTime(timezone=True))
    branch = db.relationship("Branch", lazy="joined")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    lines = db.relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(db.Model):
    __tablename__ = "journal_lines_v2"
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries_v2.id", ondelete="CASCADE"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts_v2.id", ondelete="RESTRICT"), nullable=False)
    cost_center_id = db.Column(db.Integer, db.ForeignKey("cost_centers.id", ondelete="RESTRICT"))
    party_type = db.Column(db.String(30))
    party_id = db.Column(db.Integer)
    description_ar = db.Column(db.String(500))
    debit = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    entry = db.relationship("JournalEntry", back_populates="lines")
    account = db.relationship("Account", lazy="joined")
    cost_center = db.relationship("CostCenter", lazy="joined")
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_line_nonnegative_v2"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_journal_line_one_side_v2"),
        Index("ix_journal_lines_v2_account", "account_id"),
    )

    @staticmethod
    def amount_is_valid(debit: Decimal, credit: Decimal) -> bool:
        return (debit > 0) ^ (credit > 0)


class AccountingVoucher(db.Model):
    __tablename__ = "accounting_vouchers_v2"
    id = db.Column(db.Integer, primary_key=True)
    voucher_no = db.Column(db.String(60), unique=True, nullable=False, index=True)
    voucher_type = db.Column(db.String(20), nullable=False)
    voucher_date = db.Column(db.Date, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("accounting_branches.id", ondelete="RESTRICT"), nullable=False)
    from_account_id = db.Column(db.Integer, db.ForeignKey("accounts_v2.id", ondelete="RESTRICT"), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey("accounts_v2.id", ondelete="RESTRICT"), nullable=False)
    amount = db.Column(db.Numeric(16,2), nullable=False)
    reference = db.Column(db.String(180))
    description_ar = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="posted")
    journal_entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries_v2.id", ondelete="RESTRICT"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    branch = db.relationship("Branch", lazy="joined")
    from_account = db.relationship("Account", foreign_keys=[from_account_id], lazy="joined")
    to_account = db.relationship("Account", foreign_keys=[to_account_id], lazy="joined")
    journal_entry = db.relationship("JournalEntry", lazy="joined")
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_accounting_voucher_amount_positive_v2"),
    )
