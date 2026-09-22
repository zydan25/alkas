from datetime import datetime, timezone
from ..extensions import db

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    title_ar = db.Column(db.String(220), nullable=False)
    body_ar = db.Column(db.String(1500), nullable=False)
    kind = db.Column(db.String(40), nullable=False, default="system")
    priority = db.Column(db.String(20), nullable=False, default="normal")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    push_enabled = db.Column(db.Boolean, nullable=False, default=True)
    whatsapp_enabled = db.Column(db.Boolean, nullable=False, default=True)
    sms_enabled = db.Column(db.Boolean, nullable=False, default=False)
    email_enabled = db.Column(db.Boolean, nullable=False, default=True)

class NotificationLog(db.Model):
    __tablename__ = "notification_logs"
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("notifications.id", ondelete="CASCADE"))
    channel = db.Column(db.String(30), nullable=False)
    destination = db.Column(db.String(300))
    status = db.Column(db.String(30), nullable=False, default="queued")
    provider_message_id = db.Column(db.String(240))
    sent_at = db.Column(db.DateTime(timezone=True))
