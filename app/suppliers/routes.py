from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Supplier, PurchaseInvoice
bp=Blueprint("suppliers",__name__,url_prefix="/admin/suppliers",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("suppliers/index.html",suppliers=Supplier.query.filter_by(is_active=True).order_by(Supplier.id.desc()).all(),invoices=PurchaseInvoice.query.order_by(PurchaseInvoice.id.desc()).limit(70).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"count":Supplier.query.filter_by(is_active=True).count(),"purchase_invoices":PurchaseInvoice.query.count()})