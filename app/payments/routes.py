from uuid import uuid4
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from .models import Payment
from .services import record_payment_with_accounting

bp = Blueprint("payments", __name__, url_prefix="/admin/payments")

@bp.get("")
@login_required
def index():
    rows = Payment.query.order_by(Payment.id.desc()).limit(50).all()
    return jsonify([{
        "id": row.id, "number": row.number, "invoice_id": row.invoice_id,
        "amount": str(row.amount), "method": row.method, "status": row.status
    } for row in rows])

@bp.post("")
@login_required
def create():
    data = request.get_json(silent=True) or {}
    try:
        payment = record_payment_with_accounting(
            invoice_id=int(data["invoice_id"]),
            amount=data["amount"],
            method=str(data.get("method", "cash")),
            number=str(data.get("number") or f"PAY-{uuid4().hex[:10].upper()}"),
            user_id=current_user.id,
        )
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "تعذر تسجيل الدفع أو ترحيل القيد"}), 409

    return jsonify({
        "id": payment.id,
        "number": payment.number,
        "amount": str(payment.amount),
        "status": payment.status,
    }), 201
