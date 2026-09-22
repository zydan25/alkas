from ..extensions import db


class WorkShift(db.Model):
    __tablename__ = "work_shifts"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name_ar = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_overnight = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class EmployeeShift(db.Model):
    __tablename__ = "employee_shifts"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey("work_shifts.id", ondelete="RESTRICT"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="scheduled")
