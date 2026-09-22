from datetime import datetime, timezone
from ..extensions import db


class SalaryStructure(db.Model):
    __tablename__ = "salary_structures"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(160), nullable=False, unique=True)
    base_salary = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    overtime_rate = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    commission_rate = db.Column(db.Numeric(8, 4), nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class PayrollRun(db.Model):
    __tablename__ = "payroll_runs"
    id = db.Column(db.Integer, primary_key=True)
    period_name = db.Column(db.String(80), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="draft")
    total_gross = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    total_deductions = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    total_net = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    posted_at = db.Column(db.DateTime(timezone=True))


class PayrollLine(db.Model):
    __tablename__ = "payroll_lines"
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    base_salary = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    overtime = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    bonus = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    commission = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    deductions = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    advances = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    net_salary = db.Column(db.Numeric(16, 2), nullable=False, default=0)


class EmployeeAdvance(db.Model):
    __tablename__ = "employee_advances"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    amount = db.Column(db.Numeric(16, 2), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    remaining_amount = db.Column(db.Numeric(16, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="open")
    note_ar = db.Column(db.String(400))
