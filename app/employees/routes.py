from datetime import date
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from ..extensions import db
from .models import Department, Employee, Position, Attendance
from ..users.models import Role, User

bp=Blueprint("employees",__name__,url_prefix="/admin/employees",template_folder="templates")

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
    return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all())

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    name=(request.form.get("name_ar") or "").strip()
    phone=(request.form.get("phone") or "").strip() or None
    login_username=(request.form.get("login_username") or "").strip()
    login_password=request.form.get("login_password") or ""
    login_role_id=request.form.get("login_role_id") or ""
    if not name:
        return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="اسم الموظف مطلوب"),400
    code=request.form.get("employee_code") or f"EMP-{Employee.query.count()+1:05d}"
    if Employee.query.filter_by(employee_code=code).first():
        return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="كود الموظف مستخدم"),400

    if login_username or login_password:
        if not login_username or len(login_password) < 8:
            return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="لإنشاء حساب دخول أدخل اسم المستخدم وكلمة مرور من 8 أحرف على الأقل"),400
        if User.query.filter_by(username=login_username).first():
            return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="اسم مستخدم الدخول مستخدم بالفعل"),400
        if phone and User.query.filter_by(phone=phone).first():
            return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="رقم الهاتف مرتبط بحساب مستخدم بالفعل"),400

    try:
        user=None
        if login_username:
            user=User(
                username=login_username,
                display_name=name,
                phone=phone,
                is_active=True,
            )
            user.set_password(login_password)
            if login_role_id:
                try:
                    role = db.session.get(Role, int(login_role_id))
                except (TypeError, ValueError):
                    role = None
                if not role:
                    raise ValueError("دور الموظف غير موجود")
                user.roles = [role]
            db.session.add(user)
            db.session.flush()

        employee=Employee(
            employee_code=code,
            name_ar=name,
            phone=phone,
            national_id=request.form.get("national_id") or None,
            department_id=request.form.get("department_id") or None,
            position_id=request.form.get("position_id") or None,
            hire_date=date.today(),
            base_salary=request.form.get("base_salary") or 0,
            user_id=user.id if user else None,
        )
        db.session.add(employee)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return render_template("employees/form.html",departments=Department.query.filter_by(is_active=True).all(),positions=Position.query.order_by(Position.name_ar).all(),roles=Role.query.order_by(Role.name_ar).all(),error="تعذر حفظ الموظف والحساب؛ تحقق من البيانات"),400
    return redirect(url_for("employees.ui"))

@bp.get("/api")
@login_required
def api():
    rows=Employee.query.order_by(Employee.id.desc()).limit(100).all()
    return jsonify({"departments":Department.query.filter_by(is_active=True).count(),"items":[{"id":e.id,"code":e.employee_code,"name_ar":e.name_ar,"phone":e.phone,"status":e.employment_status} for e in rows]})
