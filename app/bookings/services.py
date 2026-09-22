from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from psycopg.types.range import Range
from sqlalchemy import select

from ..accounting.models import Account
from ..audit.services import record as audit_record
from ..accounting.services import ensure_default_booking_accounts, post_entry
from ..extensions import db
from ..invoices.models import Invoice, InvoiceLine
from ..models import Booking, BookingAllocation, BookingHold, Resource, ResourceBlock, ResourceBundle, WaitlistEntry
from ..notifications.services import notify_user
from ..pricing.services import calculate_price
from ..realtime import emit_booking_event


def _as_aware(value):
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo("Asia/Aden"))


def create_hold_booking(customer_id, resource_ids=None, start_at=None, end_at=None, source="web", minutes=10, items=None):
    expire_holds()

    if items is None:
        if not resource_ids or start_at is None or end_at is None:
            raise ValueError("يجب تحديد ملعب ووقت")
        items = [
            {"resource_id": resource_id, "start_at": start_at, "end_at": end_at}
            for resource_id in dict.fromkeys(resource_ids)
        ]

    normalized = []
    for item in items:
        try:
            resource_id = int(item["resource_id"])
            item_start = _as_aware(datetime.fromisoformat(item["start_at"])) if isinstance(item["start_at"], str) else _as_aware(item["start_at"])
            item_end = _as_aware(datetime.fromisoformat(item["end_at"])) if isinstance(item["end_at"], str) else _as_aware(item["end_at"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("بيانات إحدى فترات الحجز غير صحيحة") from exc
        if item_end <= item_start:
            raise ValueError("وقت النهاية يجب أن يكون بعد وقت البداية")
        normalized.append({"resource_id": resource_id, "start_at": item_start, "end_at": item_end})

    if not normalized:
        raise ValueError("أضف فترة حجز واحدة على الأقل")

    resource_ids = list(dict.fromkeys(item["resource_id"] for item in normalized))
    for item in normalized:
        blocked = ResourceBlock.query.filter(
            ResourceBlock.resource_id == item["resource_id"],
            ResourceBlock.status == "active",
            ResourceBlock.starts_at < item["end_at"],
            ResourceBlock.ends_at > item["start_at"],
        ).first()
        if blocked:
            raise ValueError(f"الملعب محجوب في هذه الفترة: {blocked.reason_ar or blocked.reason_type}")

    resources = db.session.execute(
        select(Resource).where(Resource.id.in_(resource_ids), Resource.is_active.is_(True)).order_by(Resource.id)
    ).scalars().all()
    if len(resources) != len(resource_ids):
        raise ValueError("أحد الملاعب غير متاح أو غير موجود")
    unavailable = [r.name_ar for r in resources if r.status != "available"]
    if unavailable:
        raise ValueError("الموارد التالية غير متاحة للحجز: " + "، ".join(unavailable))

    resource_map = {resource.id: resource for resource in resources}
    booking = Booking(
        booking_number=f"BK-{uuid4().hex[:10].upper()}",
        customer_id=customer_id,
        source=source,
        status="hold",
        payment_status="unpaid",
        start_at=min(item["start_at"] for item in normalized),
        end_at=max(item["end_at"] for item in normalized),
        hold_expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
    )
    db.session.add(booking)
    db.session.flush()

    token = uuid4().hex
    hold = BookingHold.new(booking.id, token, minutes)
    booking.hold_expires_at = hold.expires_at
    db.session.add(hold)

    total = Decimal("0")
    for item in normalized:
        resource = resource_map[item["resource_id"]]
        hours = Decimal(str((item["end_at"] - item["start_at"]).total_seconds() / 3600))
        price = calculate_price(resource, item["start_at"], item["end_at"])
        total += price
        db.session.add(BookingAllocation(
            booking_id=booking.id,
            resource_id=resource.id,
            start_at=item["start_at"],
            end_at=item["end_at"],
            allocated_range=Range(item["start_at"], item["end_at"], bounds="[)"),
            price=price,
        ))

    booking.subtotal = total
    booking.total = total
    db.session.commit()
    audit_record("booking.create", "Booking", booking.id, after={"number": booking.booking_number, "total": str(booking.total), "allocations": len(booking.allocations)})
    db.session.commit()
    emit_booking_event("booking.created", booking)
    return booking, token


def expand_resource_bundles(resource_ids=None, bundle_ids=None):
    ids = list(dict.fromkeys(resource_ids or []))
    for bundle_id in dict.fromkeys(bundle_ids or []):
        bundle = db.session.get(ResourceBundle, int(bundle_id))
        if not bundle or not bundle.is_active:
            raise ValueError("حزمة الملاعب غير موجودة أو غير نشطة")
        ids.extend(resource.id for resource in bundle.resources if resource.is_active)
    return list(dict.fromkeys(ids))


def expire_holds(now=None):
    now = now or datetime.now(timezone.utc)
    rows = Booking.query.filter(
        Booking.status == "hold",
        Booking.hold_expires_at.is_not(None),
        Booking.hold_expires_at <= now,
    ).all()
    for booking in rows:
        booking.status = "expired"
        for allocation in booking.allocations:
            allocation.is_active = False
    if rows:
        db.session.commit()
    return len(rows)


def add_to_waitlist(customer_id, resource_id, desired_start_at, desired_end_at):
    last_position = db.session.query(
        db.func.max(WaitlistEntry.position)
    ).filter_by(resource_id=resource_id, status="waiting").scalar() or 0
    row = WaitlistEntry(
        customer_id=customer_id,
        resource_id=resource_id,
        desired_start_at=_as_aware(desired_start_at),
        desired_end_at=_as_aware(desired_end_at),
        position=last_position + 1,
    )
    db.session.add(row)
    db.session.commit()
    return row


def cancel_booking(booking_id, reason_ar="", user_id=None):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise ValueError("الحجز غير موجود")
    if booking.status in ("cancelled", "completed", "no_show", "expired"):
        raise ValueError("لا يمكن إلغاء هذا الحجز")
    booking.status = "cancelled"
    for allocation in booking.allocations:
        allocation.is_active = False

    from ..policies.models import BookingPolicy, RefundRequest
    from ..policies.services import cancellation_refund_percent
    policy = BookingPolicy.query.filter_by(is_default=True, is_active=True).first()
    refund_percent = cancellation_refund_percent(policy, booking.start_at) if policy else 0
    requested_refund = (Decimal(booking.paid_amount or 0) * Decimal(str(refund_percent)) / Decimal("100")).quantize(Decimal("0.01"))

    if requested_refund > 0:
        db.session.add(RefundRequest(
            booking_id=booking.id,
            requested_amount=requested_refund,
            reason_ar=reason_ar or "إلغاء الحجز",
            requested_by_id=user_id,
        ))

    # Notify the first waiting customer for any released resource.
    from ..models import Customer, WaitlistEntry
    for allocation in booking.allocations:
        waiting = WaitlistEntry.query.filter(
            WaitlistEntry.resource_id == allocation.resource_id,
            WaitlistEntry.status == "waiting",
            WaitlistEntry.desired_start_at < allocation.end_at,
            WaitlistEntry.desired_end_at > allocation.start_at,
        ).order_by(WaitlistEntry.position).first()
        if waiting:
            waiting.status = "notified"
            waiting.notified_at = datetime.now(timezone.utc)
            waiting_customer = db.session.get(Customer, waiting.customer_id)
            if waiting_customer and waiting_customer.user_id:
                notify_user(
                    waiting_customer.user_id,
                    "أصبح الوقت متاحًا",
                    f"أصبح وقت في مورد رقم {allocation.resource_id} متاحًا بعد إلغاء {booking.booking_number}.",
                    "waitlist",
                    "high",
                )

    db.session.commit()
    audit_record("booking.cancel", "Booking", booking.id, after={"status": booking.status, "refund_requested": str(requested_refund)})
    db.session.commit()
    emit_booking_event("booking.cancelled", booking)
    return booking, requested_refund


def confirm_booking(booking_id, user_id=None):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        raise ValueError("الحجز غير موجود")
    if booking.status not in ("hold", "pending"):
        raise ValueError("الحجز ليس في حالة تسمح بالتأكيد")
    if booking.hold_expires_at and booking.hold_expires_at <= datetime.now(timezone.utc):
        booking.status = "expired"
        db.session.commit()
        raise ValueError("انتهت مهلة الحجز المؤقت")

    invoice = Invoice.query.filter_by(booking_id=booking.id).first()
    newly_issued = invoice is None
    if not invoice:
        invoice = Invoice(
            number=f"INV-{uuid4().hex[:10].upper()}",
            customer_id=booking.customer_id,
            booking_id=booking.id,
            issue_date=datetime.now(timezone.utc).date(),
            status="issued",
            subtotal=booking.subtotal,
            discount=booking.discount,
            tax=booking.tax,
            total=booking.total,
            paid_amount=0,
            balance_due=booking.total,
        )
        db.session.add(invoice)
        db.session.flush()
        for allocation in booking.allocations:
            hours = Decimal(str((allocation.end_at - allocation.start_at).total_seconds() / 3600))
            db.session.add(InvoiceLine(
                invoice_id=invoice.id,
                description_ar=f"{allocation.resource.name_ar} — {allocation.start_at:%Y-%m-%d %H:%M}",
                quantity=hours,
                unit_price=(allocation.price / hours) if hours else 0,
                line_total=allocation.price,
                resource_id=allocation.resource_id,
            ))

    if newly_issued:
        receivable, revenue, branch = ensure_default_booking_accounts()
        post_entry(
            number=f"JV-INV-{invoice.id}",
            description_ar=f"إصدار فاتورة الحجز {invoice.number}",
            lines=[
                {"account_id": receivable.id, "debit": invoice.total, "credit": 0, "party_type": "customer", "party_id": booking.customer_id},
                {"account_id": revenue.id, "debit": 0, "credit": invoice.total, "party_type": "customer", "party_id": booking.customer_id},
            ],
            reference_type="invoice",
            reference_id=invoice.id,
            user_id=user_id,
            branch_id=branch.id,
        )

    booking.status = "confirmed"
    db.session.commit()
    audit_record("booking.confirm", "Booking", booking.id, after={"status": booking.status, "invoice_id": invoice.id})
    db.session.commit()

    customer = booking.customer
    if customer and customer.user_id:
        notify_user(customer.user_id, "تم تأكيد الحجز", f"تم تأكيد الحجز {booking.booking_number} بمبلغ {invoice.total}.", "booking", "high")
    emit_booking_event("booking.confirmed", booking)
    return booking, invoice
