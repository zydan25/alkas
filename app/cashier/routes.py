from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from .models import CashRegister, CashShift, CashTransaction

bp = Blueprint("cashier", __name__, url_prefix="/admin/cashier", template_folder="templates")

@bp.get("")
@login_required
def ui():
    registers = CashRegister.query.filter_by(is_active=True).order_by(CashRegister.id).all()
    shifts = CashShift.query.order_by(CashShift.id.desc()).limit(30).all()
    transactions = CashTransaction.query.order_by(CashTransaction.id.desc()).limit(30).all()
    return render_template("cashier/index.html", registers=registers, shifts=shifts, transactions=transactions)

@bp.get("/api")
@login_required
def api():
    return jsonify({
        "registers": CashRegister.query.filter_by(is_active=True).count(),
        "open_shifts": CashShift.query.filter_by(status="open").count(),
        "transactions": CashTransaction.query.count(),
    })
