from flask import Blueprint, jsonify
from .models import WorkShift, EmployeeShift

bp = Blueprint("shifts", __name__, url_prefix="/admin/shifts")

@bp.get("")
def index():
    return jsonify({
        "shifts": WorkShift.query.filter_by(is_active=True).count(),
        "scheduled": EmployeeShift.query.filter_by(status="scheduled").count(),
    })
