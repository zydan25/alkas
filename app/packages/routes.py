from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import BookingPackage, CustomerPackage
bp=Blueprint("packages",__name__,url_prefix="/admin/packages",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("packages/index.html", plans=BookingPackage.query.filter_by(is_active=True).order_by(BookingPackage.id.desc()).all(), balances=CustomerPackage.query.filter_by(status="active").order_by(CustomerPackage.id.desc()).limit(80).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"packages":BookingPackage.query.filter_by(is_active=True).count(),"customer_balances":CustomerPackage.query.filter_by(status="active").count()})