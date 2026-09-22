from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .models import FinancialClose
from .services import close_day

bp = Blueprint("closing", __name__, url_prefix="/admin/closing", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("closing.manage")


@bp.get("")
@login_required
def ui():
    if not _allowed():
        return {"error": "forbidden"}, 403
    rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(60).all()
    return render_template("closing/index.html", rows=rows)


@bp.post("/close")
@login_required
def close():
    if not _allowed():
        return {"error": "forbidden"}, 403
    try:
        close_date = date.fromisoformat(request.form.get("close_date") or date.today().isoformat())
        expected_cash = Decimal(request.form.get("expected_cash") or "0")
        actual_cash = Decimal(request.form.get("actual_cash") or "0")
    except (ValueError, TypeError):
        rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(60).all()
        return render_template("closing/index.html", rows=rows, error="بيانات الإقفال غير صحيحة"), 400

    try:
        close_day(close_date, expected_cash, actual_cash, current_user.id)
    except ValueError as exc:
        rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(60).all()
        return render_template("closing/index.html", rows=rows, error=str(exc)), 400

    return redirect(url_for("closing.ui"))


@bp.get("/api")
@login_required
def api():
    rows = FinancialClose.query.order_by(FinancialClose.id.desc()).limit(31).all()
    return jsonify([{
        "date": r.close_date.isoformat(),
        "status": r.status,
        "expected": str(r.expected_cash),
        "actual": str(r.actual_cash),
        "difference": str(r.difference)
    } for r in rows])
