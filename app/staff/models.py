from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index

from ..extensions import db


class StaffDeduction(db.Model):
    __tablename__ = "staff_deductions"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    deduction_date = db.Column(db.Date, nullable=False)
    reason_ar = db.Column(db.String(500), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ParkVisit(db.Model):
    __tablename__ = "park_visits"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    visitor_name = db.Column(db.String(180), nullable=False)
    people_count = db.Column(db.Integer, nullable=False, default=1)
    people_remaining = db.Column(db.Integer, nullable=False, default=1)
    price_per_person = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expected_end_at = db.Column(db.DateTime(timezone=True))
    closed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="SET NULL"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    __table_args__ = (
        CheckConstraint("people_count > 0", name="ck_park_visit_people_positive"),
        CheckConstraint("people_remaining >= 0 AND people_remaining <= people_count", name="ck_park_visit_remaining_valid"),
        CheckConstraint("price_per_person >= 0 AND total >= 0", name="ck_park_visit_amounts_nonnegative"),
        Index("ix_park_visits_started_status", "started_at", "status"),
    )


class ParkVisitExit(db.Model):
    __tablename__ = "park_visit_exits"
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("park_visits.id", ondelete="CASCADE"), nullable=False, index=True)
    people_count = db.Column(db.Integer, nullable=False)
    exited_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    note_ar = db.Column(db.String(400))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    __table_args__ = (
        CheckConstraint("people_count > 0", name="ck_park_exit_people_positive"),
    )
