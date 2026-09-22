from flask import Blueprint, jsonify
from .models import Invoice

bp = Blueprint("invoices", __name__, url_prefix="/admin/invoices")

@bp.get("")
def index():
    rows = Invoice.query.order_by(Invoice.id.desc()).limit(50).all()
    return jsonify([{
        "id": row.id, "number": row.number, "status": row.status,
        "total": str(row.total), "paid": str(row.paid_amount),
        "balance": str(row.balance_due)
    } for row in rows])
