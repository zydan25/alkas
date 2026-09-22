from datetime import date, time
from ..extensions import db

class PriceRule(db.Model):
    __tablename__ = "price_rules"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(180), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="CASCADE"))
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id", ondelete="CASCADE"))
    price_per_hour = db.Column(db.Numeric(16, 2), nullable=False)
    weekday = db.Column(db.Integer)  # Monday=0 ... Sunday=6
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    min_minutes = db.Column(db.Integer)
    max_minutes = db.Column(db.Integer)
    priority = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class PriceOverride(db.Model):
    __tablename__ = "price_overrides"
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    price_per_hour = db.Column(db.Numeric(16, 2), nullable=False)
    reason_ar = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
