from datetime import datetime, timezone
from ..extensions import db

class FinancialClose(db.Model):
    __tablename__ = "financial_closes"
    id = db.Column(db.Integer, primary_key=True)
    close_date = db.Column(db.Date, nullable=False, unique=True)
    status = db.Column(db.String(30), nullable=False, default="open")
    expected_cash = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    actual_cash = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    difference = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    closed_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    closed_at = db.Column(db.DateTime(timezone=True))
    note_ar = db.Column(db.String(500))
