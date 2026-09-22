from flask import Blueprint, jsonify
from datetime import date
from .models import FinancialClose

bp = Blueprint("closing", __name__, url_prefix="/admin/closing")

@bp.get("")
def index():
    rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(31).all()
    return jsonify([{"date": r.close_date.isoformat(), "status": r.status, "difference": str(r.difference)} for r in rows])
