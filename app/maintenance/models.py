from datetime import datetime, timezone
from ..extensions import db


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False)
    title_ar = db.Column(db.String(220), nullable=False)
    description_ar = db.Column(db.Text)
    priority = db.Column(db.String(20), nullable=False, default="normal")
    status = db.Column(db.String(30), nullable=False, default="open")
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime(timezone=True))


class WorkOrder(db.Model):
    __tablename__ = "maintenance_work_orders"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("maintenance_requests.id", ondelete="CASCADE"), nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    labor_cost = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    parts_cost = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    notes_ar = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default="planned")
