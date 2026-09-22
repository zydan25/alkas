from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Booking, BookingAllocation, Customer, Resource, ResourceBundle
from .services import add_to_waitlist, cancel_booking, confirm_booking, create_hold_booking, expand_resource_bundles, expire_holds

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bp.get("")
def booking_page():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=url_for("bookings.booking_page")))

    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return render_template("bookings/no_customer.html")

    resources = Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all()
    bundles = ResourceBundle.query.filter_by(is_active=True).order_by(ResourceBundle.id).all()
    return render_template("bookings/index.html", customer=customer, resources=resources, bundles=bundles)


@bp.get("/availability")
def availability():
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    resource_id = request.args.get("resource_id", type=int)
    if not start_raw or not end_raw or not resource_id:
        return jsonify({"error": "start, end, resource_id are required"}), 400

    start_at = datetime.fromisoformat(start_raw)
    end_at = datetime.fromisoformat(end_raw)
    expire_holds()
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


@bp.post("/availability/batch")
@login_required
def availability_batch():
    expire_holds()
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    results = []
    for item in items:
        try:
            resource_id = int(item["resource_id"])
            start_at = datetime.fromisoformat(item["start_at"])
            end_at = datetime.fromisoformat(item["end_at"])
        except (KeyError, TypeError, ValueError):
            results.append({"available": False, "error": "بيانات الوقت غير صحيحة"})
            continue
        conflicts = BookingAllocation.query.join(Booking).filter(
            Booking.status.in_(["hold", "pending", "confirmed", "checked_in", "in_progress"]),
            BookingAllocation.is_active.is_(True),
            BookingAllocation.resource_id == resource_id,
            BookingAllocation.start_at < end_at,
            BookingAllocation.end_at > start_at,
        ).count()
        resource = Resource.query.get(resource_id)
        results.append({
            "resource_id": resource_id,
            "available": bool(resource and resource.is_active and resource.status == "available" and conflicts == 0),
        })
    return jsonify({"available": all(x.get("available") for x in results), "items": results})


@bp.post("/quote")
@login_required
def quote():
    from ..pricing.services import calculate_price
    data = request.get_json(silent=True) or {}
    total = 0
    lines = []
    for item in data.get("items") or []:
        try:
            resource = Resource.query.get(int(item["resource_id"]))
            start_at = datetime.fromisoformat(item["start_at"])
            end_at = datetime.fromisoformat(item["end_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if not resource or not resource.is_active:
            continue
        price = calculate_price(resource, start_at, end_at)
        total += price
        lines.append({"resource_id": resource.id, "resource": resource.name_ar, "price": str(price)})
    return jsonify({"total": str(total), "lines": lines})


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
            resource_ids = expand_resource_bundles(
                [int(value) for value in data.get("resource_ids", [])],
                [int(value) for value in data.get("bundle_ids", [])],
            )
            start_at = datetime.fromisoformat(data["start_at"])
            end_at = datetime.fromisoformat(data["end_at"])
        else:
            expanded_items = []
            for item in items:
                bundle_ids = [int(v) for v in item.get("bundle_ids", [])]
                expanded = expand_resource_bundles(
                    [int(v) for v in item.get("resource_ids", [])],
                    bundle_ids,
                )
                for resource_id in expanded:
                    expanded_items.append({
                        "resource_id": resource_id,
                        "start_at": item["start_at"],
                        "end_at": item["end_at"],
                    })
            items = expanded_items
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


@bp.post("/<int:booking_id>/cancel")
@login_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer or booking.customer_id != customer.id:
        return jsonify({"error": "غير مصرح"}), 403
    try:
        booking, refund = cancel_booking(
            booking_id,
            reason_ar=(request.get_json(silent=True) or {}).get("reason_ar", "إلغاء من العميل"),
            user_id=current_user.id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "booking_id": booking.id,
        "status": booking.status,
        "requested_refund": str(refund),
    })


@bp.post("/waitlist")
@login_required
def join_waitlist():
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return jsonify({"error": "لا يوجد ملف عميل مرتبط بحسابك"}), 403
    data = request.get_json(silent=True) or {}
    try:
        row = add_to_waitlist(
            customer.id,
            int(data["resource_id"]),
            datetime.fromisoformat(data["desired_start_at"]),
            datetime.fromisoformat(data["desired_end_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": row.id, "position": row.position, "status": row.status}), 201


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
