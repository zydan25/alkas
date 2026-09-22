from datetime import datetime, timezone
from ..extensions import db

class AnnouncementCard(db.Model):
    __tablename__ = "announcement_cards"
    id = db.Column(db.Integer, primary_key=True)
    title_ar = db.Column(db.String(240), nullable=False)
    body_ar = db.Column(db.String(1000))
    card_type = db.Column(db.String(30), nullable=False, default="text")
    image_url = db.Column(db.String(800))
    video_url = db.Column(db.String(800))
    target_url = db.Column(db.String(800))
    button_text_ar = db.Column(db.String(120))
    accent_label_ar = db.Column(db.String(100))
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    priority = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="published")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def visible(self, now=None):
        now = now or datetime.now(timezone.utc)
        return (
            self.status == "published"
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or now < self.ends_at)
        )
