from datetime import datetime, timezone

from sqlalchemy import CheckConstraint

from ..extensions import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("accounts.id", ondelete="RESTRICT"))
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(180), nullable=False)
    account_type = db.Column(db.String(40), nullable=False)
    is_control = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    parent = db.relationship("Account", remote_side=[id], backref=db.backref("children", lazy="selectin"))


class JournalEntry(db.Model):
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    entry_date = db.Column(db.Date, nullable=False)
    description_ar = db.Column(db.String(500), nullable=False)
    reference_type = db.Column(db.String(60))
    reference_id = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default="draft")
    posted_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    posted_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    lines = db.relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(db.Model):
    __tablename__ = "journal_lines"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    description_ar = db.Column(db.String(500))
    debit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    cost_center = db.Column(db.String(120))

    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_line_nonnegative"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_journal_line_one_side"),
    )

    entry = db.relationship("JournalEntry", back_populates="lines")
    account = db.relationship("Account", lazy="joined")
