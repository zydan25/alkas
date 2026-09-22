from datetime import datetime, timezone
from ..extensions import db


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(140), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Position(db.Model):
    __tablename__ = "positions"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(140), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="SET NULL"))


class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name_ar = db.Column(db.String(180), nullable=False, index=True)
    phone = db.Column(db.String(40), index=True)
    national_id = db.Column(db.String(80))
    photo_url = db.Column(db.String(500))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="SET NULL"))
    position_id = db.Column(db.Integer, db.ForeignKey("positions.id", ondelete="SET NULL"))
    hire_date = db.Column(db.Date)
    employment_status = db.Column(db.String(30), nullable=False, default="active")
    base_salary = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))


class Attendance(db.Model):
    __tablename__ = "employee_attendance"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime(timezone=True))
    check_out = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(30), nullable=False, default="present")
    note_ar = db.Column(db.String(300))


class Leave(db.Model):
    __tablename__ = "employee_leaves"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="requested")
    reason_ar = db.Column(db.String(500))
