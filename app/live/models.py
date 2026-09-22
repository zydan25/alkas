from datetime import datetime, timezone
from ..extensions import db


class LiveEvent(db.Model):
    __tablename__ = "live_events"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(220), nullable=False)
    description_ar = db.Column(db.Text)
    event_type = db.Column(db.String(40), nullable=False, default="match")
    starts_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), nullable=False, default="scheduled")
    cover_url = db.Column(db.String(500))


class Stream(db.Model):
    __tablename__ = "streams"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False)
    provider = db.Column(db.String(40), nullable=False)
    stream_url = db.Column(db.String(800), nullable=False)
    playback_url = db.Column(db.String(800))
    status = db.Column(db.String(30), nullable=False, default="scheduled")


class Viewer(db.Model):
    __tablename__ = "live_viewers"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False)
    session_key = db.Column(db.String(100), nullable=False, index=True)
    joined_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    left_at = db.Column(db.DateTime(timezone=True))
