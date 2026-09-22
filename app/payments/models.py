from datetime import datetime, timezone
from ..extensions import db


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"))
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="completed")
    external_reference = db.Column(db.String(180))
    received_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    paid_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class Refund(db.Model):
    __tablename__ = "refunds"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="SET NULL"))
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    reason_code = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="requested")
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
