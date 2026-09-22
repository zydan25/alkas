from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from .models import FinancialClose

bp = Blueprint("closing", __name__, url_prefix="/admin/closing")

@bp.get("")
@login_required
def ui():
    rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(60).all()
    return render_template("closing/index.html", rows=rows)

@bp.get("/api")
@login_required
def api():
    rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(31).all()
    return jsonify([{"date": r.close_date.isoformat(), "status": r.status, "expected": str(r.expected_cash), "actual": str(r.actual_cash), "difference": str(r.difference)} for r in rows])
