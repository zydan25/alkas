from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..invoices.models import Invoice
from .models import Payment
from .services import record_payment_with_accounting

bp = Blueprint("payments", __name__, url_prefix="/admin/payments", template_folder="templates")


@bp.get("")
@login_required
def ui():
    invoices = Invoice.query.filter(Invoice.balance_due > 0).order_by(Invoice.id.desc()).limit(100).all()
    rows = Payment.query.order_by(Payment.id.desc()).limit(100).all()
    return render_template("payments/index.html", rows=rows, invoices=invoices)


@bp.get("/api")
@login_required
def api():
    rows = Payment.query.order_by(Payment.id.desc()).limit(50).all()
    return jsonify([{
        "id": row.id, "number": row.number, "invoice_id": row.invoice_id,
        "amount": str(row.amount), "method": row.method, "status": row.status
    } for row in rows])


@bp.post("/create")
@login_required
def create():
    data = request.form
    try:
        payment = record_payment_with_accounting(
            invoice_id=int(data["invoice_id"]),
            amount=data["amount"],
            method=data.get("method", "cash"),
            number=data.get("number") or f"PAY-{Payment.query.count()+1:06d}",
            user_id=current_user.id,
        )
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template("payments/index.html", rows=Payment.query.order_by(Payment.id.desc()).limit(100).all(), invoices=Invoice.query.filter(Invoice.balance_due > 0).order_by(Invoice.id.desc()).limit(100).all(), error=str(exc)), 400
    return render_template("payments/index.html", rows=Payment.query.order_by(Payment.id.desc()).limit(100).all(), invoices=Invoice.query.filter(Invoice.balance_due > 0).order_by(Invoice.id.desc()).limit(100).all(), success=f"تم تسجيل {payment.number}")
