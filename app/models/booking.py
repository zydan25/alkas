from datetime import datetime, timedelta, timezone

from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSTZRANGE

from ..extensions import db


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="hold", index=True)
    payment_status = db.Column(db.String(30), nullable=False, default="unpaid", index=True)
    source = db.Column(db.String(30), nullable=False, default="web")
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    hold_expires_at = db.Column(db.DateTime(timezone=True))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_booking_valid_time"),
        Index("ix_bookings_start_end", "start_at", "end_at"),
    )

    customer = db.relationship("Customer", back_populates="bookings")
    allocations = db.relationship("BookingAllocation", back_populates="booking", cascade="all, delete-orphan")
    holds = db.relationship("BookingHold", back_populates="booking", cascade="all, delete-orphan")


class BookingAllocation(db.Model):
    __tablename__ = "booking_allocations"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)
    allocated_range = db.Column(TSTZRANGE, nullable=False)
    price = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    __table_args__ = (
        ExcludeConstraint(
            ("resource_id", "="),
            ("allocated_range", "&&"),
            name="booking_allocations_resource_time_excl",
            using="gist",
        ),
    )

    booking = db.relationship("Booking", back_populates="allocations")
    resource = db.relationship("Resource", lazy="joined")


class BookingHold(db.Model):
    __tablename__ = "booking_holds"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(80), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    booking = db.relationship("Booking", back_populates="holds")

    @classmethod
    def new(cls, booking_id, token, minutes=10):
        return cls(
            booking_id=booking_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
        )
