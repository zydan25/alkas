from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Customer
from .models import Invoice
from .services import issue_manual_invoice

bp=Blueprint("invoices",__name__,url_prefix="/admin/invoices",template_folder="templates")

@bp.get("")
@login_required
def ui():
    rows=Invoice.query.order_by(Invoice.id.desc()).limit(100).all()
    return render_template("invoices/index.html",rows=rows)

@bp.get("/new")
@login_required
def new():
    if current_user.username != "admin" and not current_user.has_permission("invoice.manage"):
        return {"error": "forbidden"}, 403
    return render_template("invoices/form.html",customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(300).all())

@bp.post("/new")
@login_required
def create():
    if current_user.username != "admin" and not current_user.has_permission("invoice.manage"):
        return {"error": "forbidden"}, 403
    try:
        invoice=issue_manual_invoice(int(request.form["customer_id"]),request.form.get("description_ar"),request.form["amount"],current_user.id)
    except (KeyError,TypeError,ValueError) as exc:
        return render_template("invoices/form.html",customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(300).all(),error=str(exc)),400
    return redirect(url_for("invoices.ui"))

@bp.get("/api")
@login_required
def api():
    rows=Invoice.query.order_by(Invoice.id.desc()).limit(50).all()
    return jsonify([{"id":r.id,"number":r.number,"status":r.status,"total":str(r.total),"paid":str(r.paid_amount),"balance":str(r.balance_due)} for r in rows])
