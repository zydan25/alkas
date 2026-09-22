from decimal import Decimal

from ..accounting.models import Account
from ..accounting.services import post_entry
from ..extensions import db
from ..invoices.models import Invoice
from ..models import Booking
from ..notifications.services import notify_user
from ..realtime import emit_booking_event
from .models import Payment


METHOD_ACCOUNT_CODES = {
    "cash": "1100",
    "bank_transfer": "1200",
    "card": "1200",
    "payment_gateway": "1200",
    "wallet": "1100",
}


def record_payment(invoice_id, amount, method, number, user_id=None):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError("الفاتورة غير موجودة")
    amount = Decimal(str(amount))
    remaining = Decimal(invoice.total or 0) - Decimal(invoice.paid_amount or 0)
    if amount <= 0 or amount > remaining:
        raise ValueError("مبلغ الدفع غير صالح")

    payment = Payment(
        number=number,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount=amount,
        method=method,
        received_by_id=user_id,
    )
    invoice.paid_amount = Decimal(invoice.paid_amount or 0) + amount
    invoice.balance_due = Decimal(invoice.total or 0) - invoice.paid_amount
    invoice.status = "paid" if invoice.balance_due <= 0 else "partially_paid"
    db.session.add(payment)

    if invoice.booking_id:
        booking = db.session.get(Booking, invoice.booking_id)
        if booking:
            booking.paid_amount = invoice.paid_amount
            booking.payment_status = "paid" if invoice.balance_due <= 0 else "partially_paid"
            emit_booking_event("payment.received", booking)

    db.session.flush()
    return payment


def record_payment_with_accounting(invoice_id, amount, method, number, user_id=None):
    payment = record_payment(invoice_id, amount, method, number, user_id)
    invoice = db.session.get(Invoice, payment.invoice_id)

    cash_code = METHOD_ACCOUNT_CODES.get(method, "1100")
    cash = Account.query.filter_by(code=cash_code, is_active=True).first()
    revenue = Account.query.filter_by(code="4100", is_active=True).first()
    receivable = Account.query.filter_by(code="1300", is_active=True).first()

    if not cash:
        raise ValueError("حساب طريقة الدفع غير مهيأ")
    if not receivable:
        # Cash sale may still be posted directly to revenue when receivable is absent.
        receivable = revenue
    if not revenue:
        raise ValueError("حساب الإيرادات غير مهيأ")

    lines = [
        {"account_id": cash.id, "debit": payment.amount, "credit": 0, "party_type": "customer", "party_id": invoice.customer_id},
    ]
    if invoice.booking_id and invoice.status in ("paid", "partially_paid"):
        lines.append({"account_id": revenue.id, "debit": 0, "credit": payment.amount, "party_type": "customer", "party_id": invoice.customer_id})
    else:
        lines.append({"account_id": receivable.id, "debit": 0, "credit": payment.amount, "party_type": "customer", "party_id": invoice.customer_id})

    post_entry(
        number=f"JV-PAY-{payment.id}",
        description_ar=f"تحصيل الفاتورة {invoice.number}",
        lines=lines,
        reference_type="payment",
        reference_id=payment.id,
        user_id=user_id,
    )
    if invoice.booking_id:
        booking = db.session.get(Booking, invoice.booking_id)
        if booking:
            booking.payment_status = "paid" if invoice.balance_due <= 0 else "partially_paid"
    db.session.commit()
    return payment
