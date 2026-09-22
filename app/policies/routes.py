from flask import Blueprint, jsonify
from flask_login import login_required
from .models import BookingPolicy, PaymentPolicy

bp = Blueprint("policies", __name__, url_prefix="/admin/policies")

@bp.get("")
@login_required
def index():
    return jsonify({
        "booking_policies": BookingPolicy.query.filter_by(is_active=True).count(),
        "payment_policies": PaymentPolicy.query.filter_by(is_active=True).count(),
    })
