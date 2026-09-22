from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Product, Warehouse, StockMovement
bp=Blueprint("inventory",__name__,url_prefix="/admin/inventory",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("inventory/index.html",products=Product.query.filter_by(is_active=True).order_by(Product.id.desc()).limit(100).all(),warehouses=Warehouse.query.filter_by(is_active=True).all(),movements=StockMovement.query.order_by(StockMovement.id.desc()).limit(60).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"products":Product.query.filter_by(is_active=True).count(),"warehouses":Warehouse.query.filter_by(is_active=True).count(),"movements":StockMovement.query.count()})