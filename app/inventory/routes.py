from flask import Blueprint, jsonify
from .models import Product, Warehouse

bp = Blueprint("inventory", __name__, url_prefix="/admin/inventory")

@bp.get("")
def index():
    return jsonify({
        "products": Product.query.filter_by(is_active=True).count(),
        "warehouses": Warehouse.query.filter_by(is_active=True).count(),
    })
