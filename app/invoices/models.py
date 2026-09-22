from datetime import datetime, timezone
from ..extensions import db


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="RESTRICT"))
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="SET NULL"))
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default="draft")
    subtotal = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    balance_due = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    notes_ar = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    lines = db.relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(db.Model):
    __tablename__ = "invoice_lines"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description_ar = db.Column(db.String(300), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id", ondelete="SET NULL"))
    invoice = db.relationship("Invoice", back_populates="lines")
