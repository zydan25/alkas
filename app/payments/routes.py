from flask import Blueprint, jsonify
from .models import Payment

bp = Blueprint("payments", __name__, url_prefix="/admin/payments")

@bp.get("")
def index():
    rows = Payment.query.order_by(Payment.id.desc()).limit(50).all()
    return jsonify([{
        "id": row.id, "number": row.number, "invoice_id": row.invoice_id,
        "amount": str(row.amount), "method": row.method, "status": row.status
    } for row in rows])
