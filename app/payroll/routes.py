from flask import Blueprint, jsonify
from .models import PayrollRun

bp = Blueprint("payroll", __name__, url_prefix="/admin/payroll")

@bp.get("")
def index():
    rows = PayrollRun.query.order_by(PayrollRun.id.desc()).limit(24).all()
    return jsonify([{
        "id": r.id, "period": r.period_name, "status": r.status,
        "net": str(r.total_net)
    } for r in rows])
