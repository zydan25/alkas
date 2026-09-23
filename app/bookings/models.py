from datetime import datetime, timedelta, timezone
from sqlalchemy import CheckConstraint, Index
from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSTZRANGE
from ..extensions import db

class Booking(db.Model):
    __tablename__="bookings"
    id=db.Column(db.Integer,primary_key=True)
    booking_number=db.Column(db.String(40),unique=True,nullable=False,index=True)
    customer_id=db.Column(db.Integer,db.ForeignKey("customers.id",ondelete="RESTRICT"),nullable=False,index=True)
    status=db.Column(db.String(30),nullable=False,default="hold",index=True)
    payment_status=db.Column(db.String(30),nullable=False,default="unpaid",index=True)
    source=db.Column(db.String(30),nullable=False,default="web")
    start_at=db.Column(db.DateTime(timezone=True),nullable=False)
    end_at=db.Column(db.DateTime(timezone=True),nullable=False)
    subtotal=db.Column(db.Numeric(14,2),nullable=False,default=0)
    discount=db.Column(db.Numeric(14,2),nullable=False,default=0)
    tax=db.Column(db.Numeric(14,2),nullable=False,default=0)
    total=db.Column(db.Numeric(14,2),nullable=False,default=0)
    paid_amount=db.Column(db.Numeric(14,2),nullable=False,default=0)
    notes=db.Column(db.Text)
    hold_expires_at=db.Column(db.DateTime(timezone=True))
    created_by_id=db.Column(db.Integer,db.ForeignKey("users.id",ondelete="SET NULL"))
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    updated_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))
    __table_args__=(CheckConstraint("end_at > start_at",name="ck_booking_valid_time"),Index("ix_bookings_start_end","start_at","end_at"))
    customer=db.relationship("Customer",back_populates="bookings")
    allocations=db.relationship("BookingAllocation",back_populates="booking",cascade="all, delete-orphan")
    holds=db.relationship("BookingHold",back_populates="booking",cascade="all, delete-orphan")

class BookingAllocation(db.Model):
    __tablename__="booking_allocations"
    id=db.Column(db.Integer,primary_key=True)
    booking_id=db.Column(db.Integer,db.ForeignKey("bookings.id",ondelete="CASCADE"),nullable=False)
    resource_id=db.Column(db.Integer,db.ForeignKey("resources.id",ondelete="RESTRICT"),nullable=False,index=True)
    start_at=db.Column(db.DateTime(timezone=True),nullable=False)
    end_at=db.Column(db.DateTime(timezone=True),nullable=False)
    allocated_range=db.Column(TSTZRANGE,nullable=False)
    price=db.Column(db.Numeric(14,2),nullable=False,default=0)
    is_active=db.Column(db.Boolean,nullable=False,default=True,index=True)
    __table_args__=(ExcludeConstraint(("resource_id","="),("allocated_range","&&"),name="booking_allocations_resource_time_excl",where="is_active",using="gist"),)
    booking=db.relationship("Booking",back_populates="allocations")
    resource=db.relationship("Resource",lazy="joined")

class BookingHold(db.Model):
    __tablename__="booking_holds"
    id=db.Column(db.Integer,primary_key=True)
    booking_id=db.Column(db.Integer,db.ForeignKey("bookings.id",ondelete="CASCADE"),nullable=False)
    token=db.Column(db.String(80),unique=True,nullable=False,index=True)
    expires_at=db.Column(db.DateTime(timezone=True),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    booking=db.relationship("Booking",back_populates="holds")
    @classmethod
    def new(cls,booking_id,token,minutes=10):
        return cls(booking_id=booking_id,token=token,expires_at=datetime.now(timezone.utc)+timedelta(minutes=minutes))

class RecurringBooking(db.Model):
    __tablename__="recurring_bookings"
    id=db.Column(db.Integer,primary_key=True)
    customer_id=db.Column(db.Integer,db.ForeignKey("customers.id",ondelete="RESTRICT"),nullable=False)
    frequency=db.Column(db.String(30),nullable=False,default="weekly")
    starts_on=db.Column(db.Date,nullable=False)
    ends_on=db.Column(db.Date)
    occurrences=db.Column(db.Integer)
    interval_value=db.Column(db.Integer,nullable=False,default=1)
    status=db.Column(db.String(30),nullable=False,default="active")
    notes=db.Column(db.String(500))

class WaitlistEntry(db.Model):
    __tablename__="booking_waitlist"
    id=db.Column(db.Integer,primary_key=True)
    customer_id=db.Column(db.Integer,db.ForeignKey("customers.id",ondelete="RESTRICT"),nullable=False)
    resource_id=db.Column(db.Integer,db.ForeignKey("resources.id",ondelete="RESTRICT"),nullable=False)
    desired_start_at=db.Column(db.DateTime(timezone=True),nullable=False)
    desired_end_at=db.Column(db.DateTime(timezone=True),nullable=False)
    status=db.Column(db.String(30),nullable=False,default="waiting")
    position=db.Column(db.Integer,nullable=False,default=1)
    notified_at=db.Column(db.DateTime(timezone=True))

class ResourceBlock(db.Model):
    __tablename__="resource_blocks"
    id=db.Column(db.Integer,primary_key=True)
    resource_id=db.Column(db.Integer,db.ForeignKey("resources.id",ondelete="RESTRICT"),nullable=False,index=True)
    starts_at=db.Column(db.DateTime(timezone=True),nullable=False)
    ends_at=db.Column(db.DateTime(timezone=True),nullable=False)
    reason_type=db.Column(db.String(40),nullable=False)
    reason_ar=db.Column(db.String(500))
    reference_type=db.Column(db.String(80))
    reference_id=db.Column(db.Integer)
    status=db.Column(db.String(30),nullable=False,default="active")
    created_by_id=db.Column(db.Integer,db.ForeignKey("users.id",ondelete="SET NULL"))

class BookingMessage(db.Model):
    __tablename__="booking_messages"
    id=db.Column(db.Integer,primary_key=True)
    booking_id=db.Column(db.Integer,db.ForeignKey("bookings.id",ondelete="CASCADE"),nullable=False,index=True)
    sender_user_id=db.Column(db.Integer,db.ForeignKey("users.id",ondelete="SET NULL"))
    sender_role=db.Column(db.String(30),nullable=False,default="customer")
    message_type=db.Column(db.String(30),nullable=False,default="message")
    body_ar=db.Column(db.Text)
    attachment_url=db.Column(db.String(800))
    attachment_name=db.Column(db.String(240))
    attachment_mime=db.Column(db.String(120))
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    booking=db.relationship("Booking",backref=db.backref("messages",lazy="dynamic",cascade="all, delete-orphan"))
    sender=db.relationship("User",lazy="joined")


class BookingPaymentReceipt(db.Model):
    __tablename__="booking_payment_receipts"
    id=db.Column(db.Integer,primary_key=True)
    booking_id=db.Column(db.Integer,db.ForeignKey("bookings.id",ondelete="CASCADE"),nullable=False,index=True)
    uploaded_by_id=db.Column(db.Integer,db.ForeignKey("users.id",ondelete="SET NULL"))
    file_url=db.Column(db.String(800),nullable=False)
    original_name=db.Column(db.String(240),nullable=False)
    mime_type=db.Column(db.String(120))
    status=db.Column(db.String(30),nullable=False,default="pending")
    note_ar=db.Column(db.String(500))
    created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc))
    booking=db.relationship("Booking",backref=db.backref("payment_receipts",lazy="dynamic",cascade="all, delete-orphan"))
    uploaded_by=db.relationship("User",lazy="joined")
