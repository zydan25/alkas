from datetime import datetime, timezone
from ..extensions import db

class SavedReport(db.Model):
    __tablename__ = "saved_reports"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(180), nullable=False)
    report_key = db.Column(db.String(120), nullable=False, index=True)
    filters_json = db.Column(db.JSON, nullable=False, default=dict)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule = db.Column(db.String(40))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
