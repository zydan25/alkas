from datetime import datetime, timezone
from ..extensions import db

class BookingPolicy(db.Model):
    __tablename__ = "booking_policies"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(180), nullable=False, unique=True)
    cancellation_deadline_minutes = db.Column(db.Integer, nullable=False, default=360)
    refund_percent_before_deadline = db.Column(db.Numeric(6,2), nullable=False, default=100)
    refund_percent_after_deadline = db.Column(db.Numeric(6,2), nullable=False, default=0)
    deposit_percent = db.Column(db.Numeric(6,2), nullable=False, default=100)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class PaymentPolicy(db.Model):
    __tablename__ = "payment_policies"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(180), nullable=False, unique=True)
    allow_cash = db.Column(db.Boolean, nullable=False, default=True)
    allow_transfer = db.Column(db.Boolean, nullable=False, default=True)
    allow_card = db.Column(db.Boolean, nullable=False, default=True)
    allow_wallet = db.Column(db.Boolean, nullable=False, default=True)
    require_full_payment = db.Column(db.Boolean, nullable=False, default=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class RefundRequest(db.Model):
    __tablename__ = "refund_requests"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False)
    requested_amount = db.Column(db.Numeric(16,2), nullable=False)
    approved_amount = db.Column(db.Numeric(16,2))
    reason_ar = db.Column(db.String(500))
    status = db.Column(db.String(30), nullable=False, default="requested")
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
