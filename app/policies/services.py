from datetime import datetime, timezone
from decimal import Decimal

from ..accounting.models import Account
from ..accounting.services import post_entry
from ..audit.services import record as audit_record
from ..extensions import db
from ..invoices.models import Invoice
from ..models import Booking
from ..payments.models import Payment, Refund
from ..cashier.models import CashShift, CashTransaction
from ..employees.models import Employee
from .models import BookingPolicy, RefundRequest


def cancellation_refund_percent(policy, start_at, now=None):
    now = now or datetime.now(timezone.utc)
    minutes_left = (start_at - now).total_seconds() / 60
    if minutes_left >= policy.cancellation_deadline_minutes:
        return Decimal(str(policy.refund_percent_before_deadline))
    return Decimal(str(policy.refund_percent_after_deadline))


def create_refund_request(booking, requested_amount, reason_ar, user_id):
    requested_amount = Decimal(str(requested_amount))
    paid = Decimal(booking.paid_amount or 0)
    if requested_amount <= 0 or requested_amount > paid:
        raise ValueError("مبلغ الاسترجاع غير صالح")
    row = RefundRequest(
        booking_id=booking.id,
        requested_amount=requested_amount,
        reason_ar=reason_ar or "استرجاع",
        requested_by_id=user_id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def approve_refund(request_id, approved_amount=None, user_id=None):
    row = db.session.get(RefundRequest, request_id)
    if not row:
        raise ValueError("طلب الاسترجاع غير موجود")
    if row.status != "requested":
        raise ValueError("طلب الاسترجاع تمت معالجته مسبقًا")

    approved = Decimal(str(approved_amount if approved_amount is not None else row.requested_amount))
    if approved <= 0 or approved > row.requested_amount:
        raise ValueError("مبلغ الموافقة غير صالح")

    booking = db.session.get(Booking, row.booking_id)
    if not booking:
        raise ValueError("الحجز غير موجود")

    invoice = Invoice.query.filter_by(booking_id=booking.id).first()
    if not invoice:
        raise ValueError("لا توجد فاتورة مرتبطة بالحجز")
    payment = Payment.query.filter_by(invoice_id=invoice.id, status="completed").order_by(Payment.id.asc()).first()
    if not payment:
        raise ValueError("لا توجد دفعة مكتملة يمكن استرجاعها")

    already_refunded = db.session.query(db.func.coalesce(db.func.sum(Refund.amount), 0)).filter(
        Refund.payment_id == payment.id,
        Refund.status == "completed",
    ).scalar() or 0
    if approved > Decimal(payment.amount or 0) - Decimal(already_refunded):
        raise ValueError("مبلغ الاسترجاع يتجاوز الدفعة المتاحة")

    refund = Refund(
        number=f"REF-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{request_id}",
        payment_id=payment.id,
        booking_id=booking.id,
        amount=approved,
        reason_code="booking_cancellation",
        status="completed",
        requested_by_id=row.requested_by_id,
        approved_by_id=user_id,
    )
    db.session.add(refund)

    revenue = Account.query.filter_by(code="4100", is_active=True).first()
    receivable = Account.query.filter_by(code="1300", is_active=True).first()
    if not revenue or not receivable:
        raise ValueError("حسابات الإيرادات والذمم غير مهيأة")

    post_entry(
        number=f"JV-REFUND-REV-{refund.number}",
        description_ar=f"عكس إيراد بسبب استرجاع {refund.number}",
        lines=[
            {"account_id": revenue.id, "debit": approved, "credit": 0, "party_type": "customer", "party_id": booking.customer_id},
            {"account_id": receivable.id, "debit": 0, "credit": approved, "party_type": "customer", "party_id": booking.customer_id},
        ],
        reference_type="refund",
        reference_id=refund.id,
        user_id=user_id,
    )

    if payment.method == "cash":
        employee = Employee.query.filter_by(user_id=user_id, employment_status="active").first()
        shift = CashShift.query.filter_by(employee_id=employee.id, status="open").first() if employee else None
        if not shift:
            raise ValueError("الاسترجاع النقدي يحتاج وردية صندوق مفتوحة")
        db.session.add(CashTransaction(
            shift_id=shift.id,
            transaction_type="refund",
            amount=approved,
            reference_type="refund",
            reference_id=refund.id,
            description_ar=f"استرجاع {refund.number}",
        ))

    cash_account = Account.query.filter_by(code="1100", is_active=True).first()
    bank_account = Account.query.filter_by(code="1200", is_active=True).first()
    credit_account = cash_account if payment.method == "cash" else bank_account
    if not credit_account:
        raise ValueError("حساب الاسترجاع النقدي/البنكي غير مهيأ")

    post_entry(
        number=f"JV-REFUND-CASH-{refund.number}",
        description_ar=f"دفع استرجاع {refund.number}",
        lines=[
            {"account_id": receivable.id, "debit": approved, "credit": 0, "party_type": "customer", "party_id": booking.customer_id},
            {"account_id": credit_account.id, "debit": 0, "credit": approved, "party_type": "customer", "party_id": booking.customer_id},
        ],
        reference_type="refund",
        reference_id=refund.id,
        user_id=user_id,
    )

    row.approved_amount = approved
    row.approved_by_id = user_id
    row.status = "approved"
    remaining_paid = Decimal(invoice.paid_amount or 0) - approved
    invoice.paid_amount = max(Decimal("0"), remaining_paid)
    invoice.status = "refunded" if approved >= Decimal(payment.amount or 0) else "partially_refunded"
    booking.payment_status = "refunded" if invoice.status == "refunded" else "partially_refunded"
    audit_record("refund.approve", "RefundRequest", row.id, after={"amount": str(approved), "refund_id": refund.id})
    db.session.commit()
    return refund


def reject_refund(request_id, user_id=None):
    row = db.session.get(RefundRequest, request_id)
    if not row:
        raise ValueError("طلب الاسترجاع غير موجود")
    if row.status != "requested":
        raise ValueError("طلب الاسترجاع تمت معالجته مسبقًا")
    row.status = "rejected"
    row.approved_by_id = user_id
    audit_record("refund.reject", "RefundRequest", row.id, after={"status": "rejected"})
    db.session.commit()
    return row
