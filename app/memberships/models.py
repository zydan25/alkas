from datetime import date, datetime, timezone
from ..extensions import db


class MembershipPlan(db.Model):
    __tablename__ = "membership_plans"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(160), nullable=False, unique=True)
    price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    discount_percent = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    priority_booking = db.Column(db.Boolean, nullable=False, default=False)
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Membership(db.Model):
    __tablename__ = "memberships"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False)
    starts_on = db.Column(db.Date, nullable=False, default=date.today)
    ends_on = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="active")
    auto_renew = db.Column(db.Boolean, nullable=False, default=False)



class MembershipRequest(db.Model):
    __tablename__ = "membership_requests"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("membership_plans.id", ondelete="RESTRICT"), nullable=False)
    title_ar = db.Column(db.String(180), nullable=False)
    price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    auto_renew = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    cancellation_reason = db.Column(db.String(700))
    admin_note = db.Column(db.String(700))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc), onupdate=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    customer = db.relationship("Customer", lazy="joined")
    plan = db.relationship("MembershipPlan", lazy="joined")


class MembershipMessage(db.Model):
    __tablename__ = "membership_messages"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("membership_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    sender_role = db.Column(db.String(30), nullable=False, default="customer")
    body_ar = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    request = db.relationship("MembershipRequest", backref=db.backref("messages", lazy="dynamic", cascade="all, delete-orphan"))
