from decimal import Decimal

from ..accounting.models import Account
from ..audit.services import record as audit_record
from ..accounting.services import post_entry
from ..extensions import db
from ..invoices.models import Invoice
from ..models import Booking
from ..cashier.models import CashShift, CashTransaction
from ..employees.models import Employee
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
    db.session.flush()

    if invoice.booking_id:
        booking = db.session.get(Booking, invoice.booking_id)
        if booking:
            booking.paid_amount = invoice.paid_amount
            booking.payment_status = "paid" if invoice.balance_due <= 0 else "partially_paid"
            emit_booking_event("payment.received", booking)

    return payment


def record_payment_with_accounting(invoice_id, amount, method, number, user_id=None):
    payment = record_payment(invoice_id, amount, method, number, user_id)
    invoice = db.session.get(Invoice, payment.invoice_id)

    cash_code = METHOD_ACCOUNT_CODES.get(method, "1100")
    cash = Account.query.filter_by(code=cash_code, is_active=True).first()
    receivable = Account.query.filter_by(code="1300", is_active=True).first()
    if not cash or not receivable:
        raise ValueError("حساب النقدية أو الذمم غير مهيأ")

    if payment.method == "cash":
        employee = Employee.query.filter_by(user_id=user_id, employment_status="active").first()
        shift = CashShift.query.filter_by(employee_id=employee.id, status="open").first() if employee else None
        if not shift:
            raise ValueError("لا يمكن تسجيل دفع نقدي بدون وردية صندوق مفتوحة")
        db.session.add(CashTransaction(
            shift_id=shift.id,
            transaction_type="receipt",
            amount=payment.amount,
            reference_type="payment",
            reference_id=payment.id,
            description_ar=f"تحصيل {invoice.number}",
        ))

    post_entry(
        number=f"JV-PAY-{payment.id}",
        description_ar=f"تحصيل الفاتورة {invoice.number}",
        lines=[
            {"account_id": cash.id, "debit": payment.amount, "credit": 0, "party_type": "customer", "party_id": invoice.customer_id},
            {"account_id": receivable.id, "debit": 0, "credit": payment.amount, "party_type": "customer", "party_id": invoice.customer_id},
        ],
        reference_type="payment",
        reference_id=payment.id,
        user_id=user_id,
    )

    if invoice.booking_id:
        booking = db.session.get(Booking, invoice.booking_id)
        if booking and booking.customer and booking.customer.user_id:
            notify_user(
                booking.customer.user_id,
                "تم استلام الدفعة",
                f"تم تسجيل دفعة {payment.amount} للحجز {booking.booking_number}.",
                "payment",
                "high",
            )

    audit_record("payment.create", "Payment", payment.id, after={"number": payment.number, "amount": str(payment.amount), "method": payment.method})
    db.session.commit()
    return payment
