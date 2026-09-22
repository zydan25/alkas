from flask import Blueprint, jsonify
from .models import CashRegister, CashShift

bp = Blueprint("cashier", __name__, url_prefix="/admin/cashier")

@bp.get("")
def index():
    return jsonify({
        "registers": CashRegister.query.filter_by(is_active=True).count(),
        "open_shifts": CashShift.query.filter_by(status="open").count(),
    })
