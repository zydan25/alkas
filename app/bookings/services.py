from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from ..extensions import db
from ..models import Booking, BookingAllocation, BookingHold, Customer, Resource
from ..realtime import emit_booking_event


def create_hold_booking(customer_id, resource_ids, start_at, end_at, source="web", minutes=10):
    if not resource_ids:
        raise ValueError("يجب اختيار ملعب واحد على الأقل")
    if end_at <= start_at:
        raise ValueError("وقت النهاية يجب أن يكون بعد وقت البداية")

    resources = db.session.execute(
        select(Resource).where(Resource.id.in_(resource_ids), Resource.is_active.is_(True))
    ).scalars().all()

    if len(resources) != len(set(resource_ids)):
        raise ValueError("أحد الملاعب غير متاح أو غير موجود")

    booking = Booking(
        booking_number=f"BK-{uuid4().hex[:10].upper()}",
        customer_id=customer_id,
        source=source,
        status="hold",
        payment_status="unpaid",
        start_at=start_at,
        end_at=end_at,
        hold_expires_at=datetime.now(timezone.utc),
    )
    db.session.add(booking)
    db.session.flush()

    token = uuid4().hex
    booking.hold_expires_at = BookingHold.new(booking.id, token, minutes).expires_at
    db.session.add(BookingHold.new(booking.id, token, minutes))

    total = Decimal("0")
    for resource in resources:
        price = Decimal(resource.base_price or 0)
        total += price
        db.session.add(
            BookingAllocation(
                booking_id=booking.id,
                resource_id=resource.id,
                start_at=start_at,
                end_at=end_at,
                allocated_range=f"[{start_at.isoformat()},{end_at.isoformat()})",
                price=price,
            )
        )

    booking.subtotal = total
    booking.total = total
    db.session.commit()

    emit_booking_event("booking.created", booking)
    return booking, token
