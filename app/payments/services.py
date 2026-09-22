from decimal import Decimal

from ..extensions import db
from ..models import Booking
from ..realtime import emit_booking_event
from ..invoices.models import Invoice
from .models import Payment


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
