from datetime import datetime

from flask import Blueprint, jsonify, request

from ..bookings.services import create_hold_booking
from ..models import Booking, BookingAllocation, Resource
from ..realtime import emit_booking_event

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bp.get("/availability")
def availability():
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    resource_id = request.args.get("resource_id", type=int)

    if not start_raw or not end_raw or not resource_id:
        return jsonify({"error": "start, end, resource_id are required"}), 400

    start_at = datetime.fromisoformat(start_raw)
    end_at = datetime.fromisoformat(end_raw)

    conflicts = (
        BookingAllocation.query
        .join(Booking)
        .filter(
            Booking.status.in_([ "hold", "pending", "confirmed", "checked_in", "in_progress" ]),
            BookingAllocation.resource_id == resource_id,
            BookingAllocation.start_at < end_at,
            BookingAllocation.end_at > start_at,
        )
        .count()
    )
    resource = Resource.query.get_or_404(resource_id)

    return jsonify({
        "available": conflicts == 0 and resource.is_active and resource.status == "available",
        "resource_id": resource.id,
        "start": start_at.isoformat(),
        "end": end_at.isoformat(),
    })


@bp.post("/holds")
def create_hold():
    data = request.get_json(silent=True) or {}
    try:
        customer_id = int(data["customer_id"])
        resource_ids = [int(value) for value in data.get("resource_ids", [])]
        start_at = datetime.fromisoformat(data["start_at"])
        end_at = datetime.fromisoformat(data["end_at"])
        booking, token = create_hold_booking(
            customer_id=customer_id,
            resource_ids=resource_ids,
            start_at=start_at,
            end_at=end_at,
            source=data.get("source", "web"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        from ..extensions import db
        db.session.rollback()
        return jsonify({"error": "تعذر إنشاء الحجز؛ ربما يوجد تعارض زمني"}), 409

    return jsonify({
        "booking": {
            "id": booking.id,
            "number": booking.booking_number,
            "status": booking.status,
            "payment_status": booking.payment_status,
            "total": str(booking.total),
            "hold_expires_at": booking.hold_expires_at.isoformat(),
        },
        "hold_token": token,
    }), 201
