from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from ..accounting.models import Account
from ..accounting.services import post_entry
from ..extensions import db
from ..models import Customer
from .models import Invoice, InvoiceLine

def issue_manual_invoice(customer_id, description_ar, amount, user_id=None):
    customer=db.session.get(Customer, customer_id)
    if not customer: raise ValueError("العميل غير موجود")
    amount=Decimal(str(amount))
    if amount<=0: raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
    invoice=Invoice(
        number=f"INV-{uuid4().hex[:10].upper()}", customer_id=customer.id,
        issue_date=date.today(), status="issued", subtotal=amount,
        total=amount, paid_amount=Decimal("0"), balance_due=amount,
    )
    db.session.add(invoice); db.session.flush()
    db.session.add(InvoiceLine(invoice_id=invoice.id,description_ar=description_ar or "فاتورة يدوية",quantity=1,unit_price=amount,line_total=amount))
    receivable=Account.query.filter_by(code="1300",is_active=True).first()
    revenue=Account.query.filter_by(code="4100",is_active=True).first()
    if not receivable or not revenue: raise ValueError("حساب الذمم أو الإيرادات غير مهيأ")
    post_entry(
        number=f"JV-INV-{invoice.id}",description_ar=f"إصدار فاتورة {invoice.number}",
        lines=[
            {"account_id":receivable.id,"debit":amount,"credit":0,"party_type":"customer","party_id":customer.id},
            {"account_id":revenue.id,"debit":0,"credit":amount,"party_type":"customer","party_id":customer.id},
        ],reference_type="invoice",reference_id=invoice.id,user_id=user_id
    )
    db.session.commit()
    return invoice
