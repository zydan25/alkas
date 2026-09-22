from flask import Blueprint, jsonify
from .models import BookingPackage, CustomerPackage

bp = Blueprint("packages", __name__, url_prefix="/admin/packages")

@bp.get("")
def index():
    return jsonify({
        "packages": BookingPackage.query.filter_by(is_active=True).count(),
        "customer_balances": CustomerPackage.query.filter_by(status="active").count(),
    })
