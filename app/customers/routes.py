from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Customer

bp=Blueprint("customers",__name__,url_prefix="/admin/customers",template_folder="templates")

def _allowed():
    return current_user.username=="admin" or current_user.has_permission("customer.view")

@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("customers/form.html",row=None)

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    name=(request.form.get("name") or "").strip()
    if not name: return render_template("customers/form.html",row=request.form,error="اسم العميل مطلوب"),400
    if Customer.query.filter_by(phone=(request.form.get("phone") or "").strip()).first() and request.form.get("phone"):
        return render_template("customers/form.html",row=request.form,error="رقم الهاتف مستخدم"),400
    row=Customer(
        customer_code=request.form.get("customer_code") or f"CUS-{Customer.query.count()+1:05d}",
        name=name, phone=request.form.get("phone") or None, email=request.form.get("email") or None,
        notes=request.form.get("notes") or None
    )
    db.session.add(row); db.session.commit()
    return redirect(url_for("admin.customers"))
