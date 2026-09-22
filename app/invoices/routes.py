from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from .models import Invoice

bp = Blueprint("invoices", __name__, url_prefix="/admin/invoices")


@bp.get("")
@login_required
def ui():
    rows = Invoice.query.order_by(Invoice.id.desc()).limit(100).all()
    return render_template("invoices/index.html", rows=rows)


@bp.get("/api")
@login_required
def api():
    rows = Invoice.query.order_by(Invoice.id.desc()).limit(50).all()
    return jsonify([{
        "id": row.id, "number": row.number, "status": row.status,
        "total": str(row.total), "paid": str(row.paid_amount),
        "balance": str(row.balance_due)
    } for row in rows])
