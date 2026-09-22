from datetime import date
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from ..extensions import db
from .models import Department, Employee, Position, Attendance

bp=Blueprint("employees",__name__,url_prefix="/admin/employees")

def _allowed(): return current_user.username=="admin" or current_user.has_permission("employee.manage")

@bp.get("")
@login_required
def ui():
    rows=Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return render_template("employees/index.html",rows=rows,departments=Department.query.filter_by(is_active=True).all())

@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all())

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    name=(request.form.get("name_ar") or "").strip()
    if not name: return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),error="اسم الموظف مطلوب"),400
    code=request.form.get("employee_code") or f"EMP-{Employee.query.count()+1:05d}"
    if Employee.query.filter_by(employee_code=code).first(): return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),error="كود الموظف مستخدم"),400
    db.session.add(Employee(employee_code=code,name_ar=name,phone=request.form.get("phone") or None,national_id=request.form.get("national_id") or None,department_id=request.form.get("department_id") or None,position_id=request.form.get("position_id") or None,hire_date=date.today(),base_salary=request.form.get("base_salary") or 0))
    db.session.commit()
    return redirect(url_for("employees.ui"))

@bp.get("/api")
@login_required
def api():
    rows=Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return jsonify({"departments":Department.query.filter_by(is_active=True).count(),"items":[{"id":e.id,"code":e.employee_code,"name_ar":e.name_ar,"phone":e.phone,"status":e.employment_status} for e in rows]})
