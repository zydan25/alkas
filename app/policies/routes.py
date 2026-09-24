from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .models import BookingPolicy, PaymentPolicy, RefundRequest
from .services import approve_refund, reject_refund

bp = Blueprint("policies", __name__, url_prefix="/admin/policies", template_folder="templates")


def _view():
    return current_user.username == "admin" or current_user.has_permission("settings.manage") or current_user.has_permission("payment.refund")


def _approve_allowed():
    return current_user.username == "admin" or current_user.has_permission("payment.refund")


def _settings_allowed():
    return current_user.username == "admin" or current_user.has_permission("settings.manage")


@bp.get("")
@login_required
def ui():
    if not _view():
        return {"error": "forbidden"}, 403
    return render_template(
        "policies/index.html",
        booking_policies=BookingPolicy.query.filter_by(is_active=True).order_by(BookingPolicy.id).all(),
        payment_policies=PaymentPolicy.query.filter_by(is_active=True).order_by(PaymentPolicy.id).all(),
        refunds=RefundRequest.query.order_by(RefundRequest.id.desc()).limit(80).all(),
    )


@bp.post("/refunds/<int:request_id>/approve")
@login_required
def approve(request_id):
    if not _approve_allowed():
        return {"error": "forbidden"}, 403
    try:
        amount = request.form.get("approved_amount") or None
        approve_refund(request_id, amount, current_user.id)
    except (ValueError, TypeError) as exc:
        return redirect(url_for("policies.ui") + "?error=" + str(exc))
    return redirect(url_for("policies.ui"))


@bp.post("/refunds/<int:request_id>/reject")
@login_required
def reject(request_id):
    if not _approve_allowed():
        return {"error": "forbidden"}, 403
    try:
        reject_refund(request_id, current_user.id)
    except ValueError:
        pass
    return redirect(url_for("policies.ui"))


@bp.post("/booking-hold")
@login_required
def update_booking_hold():
    if not _settings_allowed():
        return {"error": "forbidden"}, 403
    try:
        minutes = int(request.form.get("hold_duration_minutes") or 60)
    except (TypeError, ValueError):
        return redirect(url_for("policies.ui") + "?error=مدة الاحتفاظ غير صحيحة")
    if minutes < 5 or minutes > 1440:
        return redirect(url_for("policies.ui") + "?error=مدة الحجز المعلق يجب أن تكون بين 5 و1440 دقيقة")

    policy = BookingPolicy.query.filter_by(is_default=True, is_active=True).order_by(BookingPolicy.id.desc()).first()
    if not policy:
        policy = BookingPolicy(
            name_ar="السياسة الافتراضية",
            hold_duration_minutes=minutes,
            cancellation_deadline_minutes=360,
            refund_percent_before_deadline=100,
            refund_percent_after_deadline=0,
            deposit_percent=100,
            is_default=True,
            is_active=True,
        )
        from ..extensions import db
        db.session.add(policy)
    else:
        policy.hold_duration_minutes = minutes
    from ..extensions import db
    db.session.commit()
    return redirect(url_for("policies.ui"))

@bp.get("/api")
@login_required
def api():
    return jsonify({
        "booking_policies": BookingPolicy.query.filter_by(is_active=True).count(),
        "payment_policies": PaymentPolicy.query.filter_by(is_active=True).count(),
        "pending_refunds": RefundRequest.query.filter_by(status="requested").count(),
    })
