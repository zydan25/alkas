from datetime import datetime, timezone
from ..extensions import db

class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(220), nullable=False)
    phone = db.Column(db.String(40))
    address_ar = db.Column(db.String(300))
    payable_balance = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class PurchaseInvoice(db.Model):
    __tablename__ = "purchase_invoices"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(60), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    total = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="open")

class SupplierPayment(db.Model):
    __tablename__ = "supplier_payments"
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    purchase_invoice_id = db.Column(db.Integer, db.ForeignKey("purchase_invoices.id", ondelete="SET NULL"))
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    method = db.Column(db.String(30), nullable=False)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
