from datetime import datetime, timezone
from ..extensions import db


class AdCampaign(db.Model):
    __tablename__ = "ad_campaigns"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(200), nullable=False)
    advertiser_ar = db.Column(db.String(180))
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    budget = db.Column(db.Numeric(16, 2))
    status = db.Column(db.String(30), nullable=False, default="draft")


class AdPlacement(db.Model):
    __tablename__ = "ad_placements"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    name_ar = db.Column(db.String(160), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class AdCreative(db.Model):
    __tablename__ = "ad_creatives"
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False)
    placement_id = db.Column(db.Integer, db.ForeignKey("ad_placements.id", ondelete="RESTRICT"), nullable=False)
    title_ar = db.Column(db.String(220))
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    target_url = db.Column(db.String(500))
    priority = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="active")
