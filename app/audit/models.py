from datetime import datetime, timezone
from ..extensions import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(100), nullable=False, index=True)
    entity_id = db.Column(db.String(80))
    before_json = db.Column(db.JSON)
    after_json = db.Column(db.JSON)
    ip_address = db.Column(db.String(80))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    actor = db.relationship("User", lazy="joined")
