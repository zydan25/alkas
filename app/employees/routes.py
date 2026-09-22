from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Department, Employee

bp = Blueprint("employees", __name__, url_prefix="/admin/employees")

@bp.get("")
@login_required
def ui():
    rows = Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return render_template("employees/index.html", rows=rows, departments=Department.query.filter_by(is_active=True).all())

@bp.get("/api")
@login_required
def api():
    rows = Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return jsonify({"departments": Department.query.filter_by(is_active=True).count(), "items": [{
        "id": e.id, "code": e.employee_code, "name_ar": e.name_ar, "phone": e.phone, "status": e.employment_status
    } for e in rows]})
