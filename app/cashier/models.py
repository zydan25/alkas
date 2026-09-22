from datetime import datetime, timezone
from ..extensions import db


class CashRegister(db.Model):
    __tablename__ = "cash_registers"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name_ar = db.Column(db.String(160), nullable=False)
    location_ar = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class CashShift(db.Model):
    __tablename__ = "cash_shifts"
    id = db.Column(db.Integer, primary_key=True)
    register_id = db.Column(db.Integer, db.ForeignKey("cash_registers.id", ondelete="RESTRICT"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"))
    opened_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at = db.Column(db.DateTime(timezone=True))
    opening_amount = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    expected_amount = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    actual_amount = db.Column(db.Numeric(16, 2))
    difference = db.Column(db.Numeric(16, 2))
    status = db.Column(db.String(20), nullable=False, default="open")


class CashTransaction(db.Model):
    __tablename__ = "cash_transactions"
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey("cash_shifts.id", ondelete="CASCADE"), nullable=False)
    transaction_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    reference_type = db.Column(db.String(80))
    reference_id = db.Column(db.Integer)
    description_ar = db.Column(db.String(400))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
