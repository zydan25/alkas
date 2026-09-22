from datetime import date, time
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..employees.models import Employee
from ..extensions import db
from .models import WorkShift, EmployeeShift
bp=Blueprint('shifts',__name__,url_prefix='/admin/shifts',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('shift.manage')
@bp.get('')
@login_required
def ui():
    return render_template('shifts/index.html',shifts=WorkShift.query.filter_by(is_active=True).order_by(WorkShift.start_time).all(),scheduled=EmployeeShift.query.order_by(EmployeeShift.work_date.desc(),EmployeeShift.id.desc()).limit(60).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed():return {'error':'forbidden'},403
    return render_template('shifts/form.html',employees=Employee.query.filter_by(employment_status='active').order_by(Employee.name_ar).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed():return {'error':'forbidden'},403
    try:
        code=(request.form.get('code') or '').strip();name=(request.form.get('name_ar') or '').strip()
        if not code or not name:raise ValueError('الكود واسم الوردية مطلوبان')
        start=time.fromisoformat(request.form['start_time']);end=time.fromisoformat(request.form['end_time'])
        if WorkShift.query.filter_by(code=code).first():raise ValueError('كود الوردية مستخدم')
        ws=WorkShift(code=code,name_ar=name,start_time=start,end_time=end,is_overnight=request.form.get('is_overnight')=='1')
        db.session.add(ws);db.session.flush()
        if request.form.get('employee_id') and request.form.get('work_date'):db.session.add(EmployeeShift(employee_id=int(request.form['employee_id']),shift_id=ws.id,work_date=date.fromisoformat(request.form['work_date']),status='scheduled'))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback();return render_template('shifts/form.html',employees=Employee.query.filter_by(employment_status='active').order_by(Employee.name_ar).all(),error=str(exc)),400
    return redirect(url_for('shifts.ui'))
@bp.get('/api')
@login_required
def api():return jsonify({'shifts':WorkShift.query.filter_by(is_active=True).count(),'scheduled':EmployeeShift.query.filter_by(status='scheduled').count()})