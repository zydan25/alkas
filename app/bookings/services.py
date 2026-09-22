from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from psycopg.types.range import Range
from sqlalchemy import select

from ..extensions import db
from ..models import Booking, BookingAllocation, BookingHold, Resource
from ..realtime import emit_booking_event


def _as_aware(value):
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo("Asia/Aden"))


def create_hold_booking(customer_id, resource_ids, start_at, end_at, source="web", minutes=10):
    resource_ids = list(dict.fromkeys(resource_ids))
    if not resource_ids:
        raise ValueError("يجب اختيار ملعب واحد على الأقل")

    start_at = _as_aware(start_at)
    end_at = _as_aware(end_at)

    if end_at <= start_at:
        raise ValueError("وقت النهاية يجب أن يكون بعد وقت البداية")

    resources = db.session.execute(
        select(Resource)
        .where(Resource.id.in_(resource_ids), Resource.is_active.is_(True))
        .order_by(Resource.id)
    ).scalars().all()

    if len(resources) != len(resource_ids):
        raise ValueError("أحد الملاعب غير متاح أو غير موجود")

    booking = Booking(
        booking_number=f"BK-{uuid4().hex[:10].upper()}",
        customer_id=customer_id,
        source=source,
        status="hold",
        payment_status="unpaid",
        start_at=start_at,
        end_at=end_at,
        hold_expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
    )
    db.session.add(booking)
    db.session.flush()

    token = uuid4().hex
    hold = BookingHold.new(booking.id, token, minutes)
    booking.hold_expires_at = hold.expires_at
    db.session.add(hold)

    hours = Decimal(str((end_at - start_at).total_seconds() / 3600))
    total = Decimal("0")

    for resource in resources:
        price = (Decimal(resource.base_price or 0) * hours).quantize(Decimal("0.01"))
        total += price
        db.session.add(
            BookingAllocation(
                booking_id=booking.id,
                resource_id=resource.id,
                start_at=start_at,
                end_at=end_at,
                allocated_range=Range(start_at, end_at, bounds="[)"),
                price=price,
            )
        )

    booking.subtotal = total
    booking.total = total
    db.session.commit()

    emit_booking_event("booking.created", booking)
    return booking, token
