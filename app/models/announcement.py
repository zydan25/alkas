from datetime import datetime, timezone

from ..extensions import db


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title_ar = db.Column(db.String(220), nullable=False)
    body_ar = db.Column(db.Text)
    card_type = db.Column(db.String(30), nullable=False, default="text")
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    target_url = db.Column(db.String(500))
    button_text_ar = db.Column(db.String(120))
    priority = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="published")
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def is_visible_now(self, now=None):
        now = now or datetime.now(timezone.utc)
        if self.status != "published":
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now >= self.ends_at:
            return False
        return True
