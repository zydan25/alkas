from flask import Blueprint, jsonify
from .models import Supplier

bp = Blueprint("suppliers", __name__, url_prefix="/admin/suppliers")

@bp.get("")
def index():
    return jsonify({"count": Supplier.query.filter_by(is_active=True).count()})
