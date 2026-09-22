from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..employees.models import Employee
from ..extensions import db
from .models import CashRegister, CashShift, CashTransaction

bp = Blueprint("cashier", __name__, url_prefix="/admin/cashier", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("cashier.manage")


@bp.get("")
@login_required
def ui():
    registers = CashRegister.query.filter_by(is_active=True).order_by(CashRegister.id).all()
    shifts = CashShift.query.order_by(CashShift.id.desc()).limit(30).all()
    transactions = CashTransaction.query.order_by(CashTransaction.id.desc()).limit(30).all()
    return render_template("cashier/index.html", registers=registers, shifts=shifts, transactions=transactions)


@bp.get("/open")
@login_required
def open_form():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return render_template("cashier/open.html", registers=CashRegister.query.filter_by(is_active=True).all())


@bp.post("/open")
@login_required
def open_shift():
    if not _allowed():
        return {"error": "forbidden"}, 403
    try:
        register_id = int(request.form["register_id"])
        opening_amount = request.form.get("opening_amount") or 0
    except (KeyError, ValueError, TypeError):
        return render_template("cashier/open.html", registers=CashRegister.query.filter_by(is_active=True).all(), error="بيانات الوردية غير صحيحة"), 400
    register = db.session.get(CashRegister, register_id)
    if not register or not register.is_active:
        return render_template("cashier/open.html", registers=CashRegister.query.filter_by(is_active=True).all(), error="الصندوق غير موجود"), 400
    if CashShift.query.filter_by(register_id=register.id, status="open").first():
        return render_template("cashier/open.html", registers=CashRegister.query.filter_by(is_active=True).all(), error="هذا الصندوق لديه وردية مفتوحة بالفعل"), 400
    employee = Employee.query.filter_by(user_id=current_user.id, employment_status="active").first()
    if not employee:
        return render_template("cashier/open.html", registers=CashRegister.query.filter_by(is_active=True).all(), error="الحساب غير مرتبط بموظف"), 400
    shift = CashShift(register_id=register.id, employee_id=employee.id, opening_amount=opening_amount)
    db.session.add(shift)
    db.session.commit()
    return redirect(url_for("cashier.ui"))


@bp.post("/<int:shift_id>/close")
@login_required
def close_shift(shift_id):
    if not _allowed():
        return {"error": "forbidden"}, 403
    shift = db.session.get(CashShift, shift_id)
    if not shift or shift.status != "open":
        return {"error": "الوردية غير موجودة أو مغلقة"}, 400
    try:
        actual = request.form["actual_amount"]
    except KeyError:
        return {"error": "المبلغ الفعلي مطلوب"}, 400
    from decimal import Decimal
    expected = Decimal(shift.opening_amount or 0)
    transactions = CashTransaction.query.filter_by(shift_id=shift.id).all()
    for tx in transactions:
        if tx.transaction_type in ("sale", "receipt", "deposit"):
            expected += Decimal(tx.amount or 0)
        else:
            expected -= Decimal(tx.amount or 0)
    shift.expected_amount = expected
    shift.actual_amount = Decimal(actual)
    shift.difference = shift.actual_amount - expected
    from datetime import datetime, timezone
    shift.status = "closed"
    shift.closed_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for("cashier.ui"))


@bp.get("/api")
@login_required
def api():
    return jsonify({
        "registers": CashRegister.query.filter_by(is_active=True).count(),
        "open_shifts": CashShift.query.filter_by(status="open").count(),
        "transactions": CashTransaction.query.count(),
    })
