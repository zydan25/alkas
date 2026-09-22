from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from psycopg.types.range import Range
from sqlalchemy import select

from ..extensions import db
from ..invoices.models import Invoice, InvoiceLine
from ..models import Booking, BookingAllocation, BookingHold, Resource
from ..notifications.services import notify_user
from ..realtime import emit_booking_event


def _as_aware(value):
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo("Asia/Aden"))


def create_hold_booking(customer_id, resource_ids=None, start_at=None, end_at=None, source="web", minutes=10, items=None):
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
    resources = db.session.execute(
        select(Resource).where(Resource.id.in_(resource_ids), Resource.is_active.is_(True)).order_by(Resource.id)
    ).scalars().all()
    if len(resources) != len(resource_ids):
        raise ValueError("أحد الملاعب غير متاح أو غير موجود")

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
        price = (Decimal(resource.base_price or 0) * hours).quantize(Decimal("0.01"))
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
    emit_booking_event("booking.created", booking)
    return booking, token


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
            db.session.add(InvoiceLine(
                invoice_id=invoice.id,
                description_ar=f"{allocation.resource.name_ar} — {allocation.start_at:%Y-%m-%d %H:%M}",
                quantity=Decimal(str((allocation.end_at - allocation.start_at).total_seconds() / 3600)),
                unit_price=allocation.price / Decimal(str((allocation.end_at - allocation.start_at).total_seconds() / 3600)),
                line_total=allocation.price,
                resource_id=allocation.resource_id,
            ))

    booking.status = "confirmed"
    db.session.commit()
    emit_booking_event("booking.confirmed", booking)
    return booking, invoice
