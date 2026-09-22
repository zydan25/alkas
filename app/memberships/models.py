from datetime import date
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
