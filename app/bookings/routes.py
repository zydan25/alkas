from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Booking, BookingAllocation, Customer, Resource
from .services import confirm_booking, create_hold_booking

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bp.get("")
def booking_page():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for("bookings.booking_page")))

    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return render_template("bookings/no_customer.html")

    resources = Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all()
    return render_template("bookings/index.html", customer=customer, resources=resources)


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
        BookingAllocation.query.join(Booking).filter(
            Booking.status.in_(["hold", "pending", "confirmed", "checked_in", "in_progress"]),
            BookingAllocation.resource_id == resource_id,
            BookingAllocation.start_at < end_at,
            BookingAllocation.end_at > start_at,
        ).count()
    )
    resource = Resource.query.get_or_404(resource_id)
    return jsonify({
        "available": conflicts == 0 and resource.is_active and resource.status == "available" and end_at > start_at,
        "resource_id": resource.id, "start": start_at.isoformat(), "end": end_at.isoformat(),
    })


@bp.post("/holds")
@login_required
def create_hold():
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return jsonify({"error": "لا يوجد ملف عميل مرتبط بحسابك"}), 403

    data = request.get_json(silent=True) or {}
    try:
        items = data.get("items")
        if items is None:
            resource_ids = [int(value) for value in data.get("resource_ids", [])]
            start_at = datetime.fromisoformat(data["start_at"])
            end_at = datetime.fromisoformat(data["end_at"])
        else:
            resource_ids = None
            start_at = end_at = None

        booking, token = create_hold_booking(
            customer_id=customer.id,
            resource_ids=resource_ids,
            start_at=start_at,
            end_at=end_at,
            items=items,
            source=data.get("source", "web"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "تعذر إنشاء الحجز؛ ربما يوجد تعارض زمني"}), 409

    return jsonify({
        "booking": {
            "id": booking.id, "number": booking.booking_number, "status": booking.status,
            "payment_status": booking.payment_status, "total": str(booking.total),
            "hold_expires_at": booking.hold_expires_at.isoformat(), "allocations": len(booking.allocations),
        },
        "hold_token": token,
    }), 201


@bp.post("/<int:booking_id>/confirm")
@login_required
def confirm(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer or booking.customer_id != customer.id:
        return jsonify({"error": "غير مصرح"}), 403
    try:
        booking, invoice = confirm_booking(booking_id, current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "booking_id": booking.id, "status": booking.status,
        "invoice_id": invoice.id, "invoice_number": invoice.number,
        "total": str(invoice.total), "balance_due": str(invoice.balance_due),
    })
