from datetime import date

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..audit.services import record as audit_record
from ..extensions import db
from .models import Attendance, Department, Employee, Position
from ..users.models import Permission, Role, User

bp = Blueprint("employees", __name__, url_prefix="/admin/employees", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("employee.manage")


def _context(**extra):
    data = {
        "departments": Department.query.filter_by(is_active=True).all(),
        "positions": Position.query.order_by(Position.name_ar).all(),
        "roles": Role.query.order_by(Role.name_ar).all(),
    }
    data.update(extra)
    return data


def _default_staff_role():
    """Baseline role: enough for the employee app, but not sensitive approval/chat rights."""
    role = Role.query.filter_by(name="staff_default").first()
    if not role:
        role = Role(name="staff_default", name_ar="موظف تشغيل", is_system=True)
        db.session.add(role)
        db.session.flush()

    baseline = {
        "staff.access": "دخول لوحة الموظف",
        "staff.finance.view": "عرض الحساب المالي للموظف",
        "staff.park.manage": "إدارة دخول الحديقة",
        "staff.cash.manage": "إدارة الصندوق والوردية",
    }
    for key, name_ar in baseline.items():
        permission = Permission.query.filter_by(key=key).first()
        if not permission:
            permission = Permission(key=key, name_ar=name_ar, is_active=True)
            db.session.add(permission)
            db.session.flush()
        if permission not in role.permissions:
            role.permissions.append(permission)

    return role


def _render_form(error=None, employee=None, user=None):
    role_id = user.roles[0].id if user and user.roles else None
    return render_template(
        "employees/form.html",
        employee=employee,
        user=user,
        current_role_id=role_id,
        is_edit=employee is not None,
        error=error,
        **_context(),
    )


def _user_for_employee(employee):
    return db.session.get(User, employee.user_id) if employee.user_id else None


@bp.get("")
@login_required
def ui():
    if not _allowed():
        return {"error": "forbidden"}, 403
    rows = (
        Employee.query
        .filter(Employee.employment_status != "deleted")
        .order_by(Employee.id.desc())
        .limit(100)
        .all()
    )
    return render_template(
        "employees/index.html",
        rows=rows,
        departments=Department.query.filter_by(is_active=True).all(),
    )


@bp.get("/new")
@login_required
def new():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return _render_form()


@bp.post("/new")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403

    name = (request.form.get("name_ar") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    login_username = (request.form.get("login_username") or "").strip()
    login_password = request.form.get("login_password") or ""
    login_role_id = (request.form.get("login_role_id") or "").strip()

    if not name:
        return _render_form("اسم الموظف مطلوب"), 400
    if not login_username:
        return _render_form("اسم المستخدم مطلوب؛ كل موظف جديد يحصل على حساب دخول تلقائيًا"), 400
    if len(login_password) < 8:
        return _render_form("كلمة مرور الموظف يجب أن تكون 8 أحرف على الأقل"), 400

    if User.query.filter(func.lower(User.username) == login_username.casefold()).first():
        return _render_form("اسم المستخدم مستخدم بالفعل؛ اختر اسمًا آخر"), 400
    if phone and User.query.filter(User.phone == phone).first():
        return _render_form("رقم الهاتف مرتبط بحساب مستخدم آخر"), 400

    code = request.form.get("employee_code") or f"EMP-{Employee.query.count() + 1:05d}"
    if Employee.query.filter_by(employee_code=code).first():
        return _render_form("كود الموظف مستخدم"), 400

    try:
        role = _default_staff_role()
        if login_role_id:
            role = db.session.get(Role, int(login_role_id))
            if not role:
                raise ValueError("دور الموظف غير موجود")

        user = User(
            username=login_username,
            display_name=name,
            phone=phone,
            is_active=True,
            roles=[role],
        )
        user.set_password(login_password)
        db.session.add(user)
        db.session.flush()

        employee = Employee(
            employee_code=code,
            name_ar=name,
            phone=phone,
            national_id=request.form.get("national_id") or None,
            department_id=request.form.get("department_id") or None,
            position_id=request.form.get("position_id") or None,
            hire_date=date.today(),
            base_salary=request.form.get("base_salary") or 0,
            employment_status="active",
            user_id=user.id,
        )
        db.session.add(employee)
        db.session.flush()

        audit_record(
            "employee.create",
            "Employee",
            employee.id,
            after={
                "name_ar": employee.name_ar,
                "user_id": user.id,
                "username": user.username,
                "role": role.name,
            },
        )
        db.session.commit()
    except (ValueError, TypeError):
        db.session.rollback()
        return _render_form("بيانات إنشاء الموظف أو الدور غير صحيحة"), 400
    except Exception:
        db.session.rollback()
        return _render_form("تعذر إنشاء الموظف وحساب الدخول؛ تحقق من البيانات"), 400

    return redirect(url_for("employees.detail", employee_id=employee.id), code=303)


@bp.get("/<int:employee_id>")
@login_required
def detail(employee_id):
    if not _allowed():
        return {"error": "forbidden"}, 403

    employee = Employee.query.get_or_404(employee_id)
    user = _user_for_employee(employee)
    return render_template(
        "employees/detail.html",
        employee=employee,
        user=user,
        attendance=(
            Attendance.query
            .filter_by(employee_id=employee.id)
            .order_by(Attendance.work_date.desc())
            .limit(20)
            .all()
        ),
    )


@bp.get("/<int:employee_id>/edit")
@login_required
def edit(employee_id):
    if not _allowed():
        return {"error": "forbidden"}, 403

    employee = Employee.query.get_or_404(employee_id)
    return _render_form(employee=employee, user=_user_for_employee(employee))


@bp.post("/<int:employee_id>/edit")
@login_required
def update(employee_id):
    if not _allowed():
        return {"error": "forbidden"}, 403

    employee = Employee.query.get_or_404(employee_id)
    name = (request.form.get("name_ar") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    login_username = (request.form.get("login_username") or "").strip()
    login_password = request.form.get("login_password") or ""
    login_role_id = (request.form.get("login_role_id") or "").strip()

    if not name:
        return _render_form("اسم الموظف مطلوب", employee=employee, user=_user_for_employee(employee)), 400
    if not login_username:
        return _render_form("اسم المستخدم مطلوب", employee=employee, user=_user_for_employee(employee)), 400

    try:
        user = _user_for_employee(employee)

        if user is None:
            existing = User.query.filter(func.lower(User.username) == login_username.casefold()).first()
            if existing:
                raise ValueError("اسم المستخدم مستخدم بالفعل، اختر اسمًا آخر")
            if phone and User.query.filter(User.phone == phone).first():
                raise ValueError("رقم الهاتف مرتبط بحساب مستخدم آخر")
            if len(login_password) < 8:
                raise ValueError("أدخل كلمة مرور 8 أحرف على الأقل لإنشاء حساب الموظف")

            role = db.session.get(Role, int(login_role_id)) if login_role_id else _default_staff_role()
            if not role:
                raise ValueError("دور الموظف غير موجود")

            user = User(
                username=login_username,
                display_name=name,
                phone=phone,
                is_active=True,
                roles=[role],
            )
            user.set_password(login_password)
            db.session.add(user)
            db.session.flush()
            employee.user_id = user.id
        else:
            conflict = User.query.filter(
                User.id != user.id,
                func.lower(User.username) == login_username.casefold(),
            ).first()
            if conflict:
                raise ValueError("اسم المستخدم مستخدم بالفعل، اختر اسمًا آخر")
            phone_conflict = User.query.filter(
                User.id != user.id,
                User.phone == phone,
            ).first() if phone else None
            if phone_conflict:
                raise ValueError("رقم الهاتف مرتبط بحساب مستخدم آخر")

            user.username = login_username
            user.display_name = name
            user.phone = phone
            if login_password:
                if len(login_password) < 8:
                    raise ValueError("كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل")
                user.set_password(login_password)

            role = db.session.get(Role, int(login_role_id)) if login_role_id else _default_staff_role()
            if not role:
                raise ValueError("دور الموظف غير موجود")
            user.roles = [role]
            user.is_active = request.form.get("employment_status", employee.employment_status) == "active"

        employee.name_ar = name
        employee.phone = phone
        employee.national_id = request.form.get("national_id") or None
        employee.department_id = request.form.get("department_id") or None
        employee.position_id = request.form.get("position_id") or None
        employee.base_salary = request.form.get("base_salary") or 0
        employee.employment_status = request.form.get("employment_status") or "active"
        user.is_active = employee.employment_status == "active"

        audit_record(
            "employee.update",
            "Employee",
            employee.id,
            after={
                "name_ar": employee.name_ar,
                "user_id": employee.user_id,
                "username": user.username,
                "role": user.roles[0].name if user.roles else None,
                "status": employee.employment_status,
            },
        )
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return _render_form(str(exc), employee=employee, user=_user_for_employee(employee)), 400
    except Exception:
        db.session.rollback()
        return _render_form("تعذر تحديث الموظف وحساب الدخول"), 400

    return redirect(url_for("employees.detail", employee_id=employee.id), code=303)


@bp.post("/<int:employee_id>/delete")
@login_required
def delete(employee_id):
    if not _allowed():
        return {"error": "forbidden"}, 403

    employee = Employee.query.get_or_404(employee_id)
    if employee.user_id == current_user.id:
        return {"error": "لا يمكن حذف أو تعطيل حسابك من هنا"}, 400

    employee.employment_status = "deleted"
    user = _user_for_employee(employee)
    if user:
        user.is_active = False

    audit_record(
        "employee.delete",
        "Employee",
        employee.id,
        after={"status": "deleted", "user_id": employee.user_id},
    )
    db.session.commit()
    return redirect(url_for("employees.ui"), code=303)


@bp.get("/api")
@login_required
def api():
    if not _allowed():
        return {"error": "forbidden"}, 403

    rows = (
        Employee.query
        .filter(Employee.employment_status != "deleted")
        .order_by(Employee.id.desc())
        .limit(100)
        .all()
    )
    items = []
    for employee in rows:
        user = _user_for_employee(employee)
        items.append(
            {
                "id": employee.id,
                "code": employee.employee_code,
                "name_ar": employee.name_ar,
                "phone": employee.phone,
                "status": employee.employment_status,
                "username": user.username if user else None,
            }
        )
    return jsonify(
        {
            "departments": Department.query.filter_by(is_active=True).count(),
            "items": items,
        }
    )
