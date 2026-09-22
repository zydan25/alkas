from flask import Blueprint, jsonify
from .models import Employee, Department

bp = Blueprint("employees", __name__, url_prefix="/admin/employees")

@bp.get("")
def index():
    rows = Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return jsonify({
        "departments": Department.query.filter_by(is_active=True).count(),
        "items": [{
            "id": e.id, "code": e.employee_code, "name_ar": e.name_ar,
            "phone": e.phone, "status": e.employment_status
        } for e in rows]
    })
