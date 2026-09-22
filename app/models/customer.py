from datetime import datetime, timezone

from ..extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    customer_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    phone = db.Column(db.String(40), index=True)
    email = db.Column(db.String(180))
    notes = db.Column(db.Text)
    credit_balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", lazy="joined")
    bookings = db.relationship("Booking", back_populates="customer", lazy="dynamic")
