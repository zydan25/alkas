from datetime import date

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..employees.models import Attendance, Employee
from ..maintenance.models import MaintenanceRequest
from ..models import Booking

bp = Blueprint("staff", __name__, url_prefix="/staff", template_folder="templates")


def _employee():
    return Employee.query.filter_by(user_id=current_user.id, employment_status="active").first()


@bp.get("")
@login_required
def dashboard():
    employee = _employee()
    if not employee:
        return render_template("staff/no_profile.html")

    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=employee.id, work_date=today).first()
    open_tasks = MaintenanceRequest.query.filter_by(assigned_employee_id=employee.id).filter(
        MaintenanceRequest.status.in_(["open", "in_progress"])
    ).order_by(MaintenanceRequest.id.desc()).limit(12).all()
    bookings_count = Booking.query.filter(Booking.status.in_(["confirmed", "checked_in", "in_progress"])).count()
    return render_template("staff/dashboard.html", employee=employee, attendance=attendance, open_tasks=open_tasks, bookings_count=bookings_count)


@bp.get("/attendance")
@login_required
def attendance():
    employee = _employee()
    if not employee:
        return render_template("staff/no_profile.html")
    rows = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.work_date.desc()).limit(60).all()
    return render_template("staff/attendance.html", employee=employee, rows=rows)
