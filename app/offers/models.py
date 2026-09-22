from datetime import datetime, timezone
from ..extensions import db


class Offer(db.Model):
    __tablename__ = "offers"
    id = db.Column(db.Integer, primary_key=True)
    title_ar = db.Column(db.String(220), nullable=False)
    body_ar = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    discount_percent = db.Column(db.Numeric(6, 2))
    fixed_discount = db.Column(db.Numeric(16, 2))
    status = db.Column(db.String(30), nullable=False, default="draft")
    priority = db.Column(db.Integer, nullable=False, default=0)


class Coupon(db.Model):
    __tablename__ = "coupons"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False, index=True)
    offer_id = db.Column(db.Integer, db.ForeignKey("offers.id", ondelete="SET NULL"))
    usage_limit = db.Column(db.Integer)
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    valid_from = db.Column(db.DateTime(timezone=True))
    valid_until = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class OfferComment(db.Model):
    __tablename__ = "offer_comments"
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"))
    body_ar = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class OfferInquiry(db.Model):
    __tablename__ = "offer_inquiries"
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"))
    question_ar = db.Column(db.String(1000), nullable=False)
    answer_ar = db.Column(db.String(1500))
    status = db.Column(db.String(30), nullable=False, default="open")
