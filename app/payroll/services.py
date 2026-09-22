from datetime import datetime, timezone
from decimal import Decimal

from ..accounting.models import Account
from ..accounting.services import post_entry
from ..audit.services import record as audit_record
from ..employees.models import Employee
from ..extensions import db
from .models import PayrollLine, PayrollRun


def generate_payroll(period_name, start_date, end_date, user_id=None):
    period_name = (period_name or "").strip()
    if not period_name:
        raise ValueError("اسم دورة الرواتب مطلوب")
    if end_date < start_date:
        raise ValueError("نهاية الفترة قبل بدايتها")
    if PayrollRun.query.filter_by(period_name=period_name).first():
        raise ValueError("دورة الرواتب موجودة")

    employees = Employee.query.filter_by(employment_status="active").order_by(Employee.id).all()
    if not employees:
        raise ValueError("لا يوجد موظفون نشطون")

    run = PayrollRun(
        period_name=period_name,
        start_date=start_date,
        end_date=end_date,
        status="draft",
    )
    db.session.add(run)
    db.session.flush()

    gross = Decimal("0")
    deductions = Decimal("0")
    net = Decimal("0")
    for employee in employees:
        base = Decimal(employee.base_salary or 0)
        line = PayrollLine(
            payroll_run_id=run.id,
            employee_id=employee.id,
            base_salary=base,
            overtime=Decimal("0"),
            bonus=Decimal("0"),
            commission=Decimal("0"),
            deductions=Decimal("0"),
            advances=Decimal("0"),
            net_salary=base,
        )
        db.session.add(line)
        gross += base
        net += base

    run.total_gross = gross
    run.total_deductions = deductions
    run.total_net = net
    audit_record(
        "payroll.generate",
        "PayrollRun",
        run.id,
        after={"period": period_name, "employees": len(employees), "net": str(net)},
    )
    db.session.commit()
    return run


def post_payroll(run_id, user_id=None):
    run = db.session.get(PayrollRun, run_id)
    if not run or run.status != "draft":
        raise ValueError("دورة الرواتب غير قابلة للترحيل")

    expense = Account.query.filter_by(code="5100", is_active=True).first()
    liability = Account.query.filter_by(code="2200", is_active=True).first()
    if not expense or not liability:
        raise ValueError("حساب مصروف الرواتب 5100 أو الرواتب المستحقة 2200 غير مهيأ")

    post_entry(
        number=f"JV-PAYROLL-{run.id}",
        description_ar=f"ترحيل رواتب {run.period_name}",
        lines=[
            {"account_id": expense.id, "debit": run.total_net, "credit": 0},
            {"account_id": liability.id, "debit": 0, "credit": run.total_net},
        ],
        reference_type="payroll",
        reference_id=run.id,
        user_id=user_id,
    )
    run.status = "posted"
    run.posted_at = datetime.now(timezone.utc)
    audit_record(
        "payroll.post",
        "PayrollRun",
        run.id,
        after={"status": run.status, "net": str(run.total_net)},
    )
    db.session.commit()
    return run
