from datetime import datetime, timezone
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..employees.models import Employee
from ..extensions import db
from ..resources.models import Resource
from .models import MaintenanceRequest
from .services import block_resource
bp=Blueprint('maintenance',__name__,url_prefix='/admin/maintenance',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('maintenance.manage')
@bp.get('')
@login_required
def ui():
    rows=MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(100).all()
    return render_template('maintenance/index.html',rows=rows)
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('maintenance/form.html',resources=Resource.query.filter_by(is_active=True).order_by(Resource.id).all(),employees=Employee.query.filter_by(employment_status='active').order_by(Employee.name_ar).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        resource_id=int(request.form['resource_id']); title=(request.form.get('title_ar') or '').strip()
        if not title: raise ValueError('عنوان البلاغ مطلوب')
        row=MaintenanceRequest(resource_id=resource_id,title_ar=title,description_ar=request.form.get('description_ar'),priority=request.form.get('priority','normal'),status='open',reported_by_id=current_user.id,assigned_employee_id=int(request.form['assigned_employee_id']) if request.form.get('assigned_employee_id') else None)
        db.session.add(row);db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback();return render_template('maintenance/form.html',resources=Resource.query.filter_by(is_active=True).all(),employees=Employee.query.filter_by(employment_status='active').all(),error=str(exc)),400
    return redirect(url_for('maintenance.ui'))
@bp.post('/<int:request_id>/status')
@login_required
def update_status(request_id):
    if not _allowed(): return {'error':'forbidden'},403
    row=db.session.get(MaintenanceRequest,request_id)
    if not row:return {'error':'البلاغ غير موجود'},404
    status=request.form.get('status','open')
    if status not in {'open','in_progress','resolved','cancelled'}:return {'error':'حالة غير صحيحة'},400
    if status=='in_progress':
        try:block_resource(row.id)
        except ValueError as exc:db.session.rollback();return {'error':str(exc)},400
    else:
        row.status=status
        row.resolved_at=datetime.now(timezone.utc) if status=='resolved' else None
        if status=='resolved':
            resource=db.session.get(Resource,row.resource_id)
            if resource:resource.status='available'
        db.session.commit()
    return redirect(url_for('maintenance.ui'))
@bp.get('/api')
@login_required
def api():
    rows=MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(50).all()
    return jsonify([{'id':r.id,'resource_id':r.resource_id,'title_ar':r.title_ar,'priority':r.priority,'status':r.status} for r in rows])