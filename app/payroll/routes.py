from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import PayrollRun
from .services import generate_payroll, post_payroll

bp=Blueprint('payroll',__name__,url_prefix='/admin/payroll',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('payroll.manage')

@bp.get('')
@login_required
def ui():
    return render_template('payroll/index.html',rows=PayrollRun.query.order_by(PayrollRun.id.desc()).limit(60).all())

@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('payroll/form.html',today=date.today())

@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        run=generate_payroll(request.form.get('period_name'),date.fromisoformat(request.form['start_date']),date.fromisoformat(request.form['end_date']),current_user.id)
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback()
        return render_template('payroll/form.html',today=date.today(),error=str(exc)),400
    return redirect(url_for('payroll.ui'))

@bp.post('/<int:run_id>/post')
@login_required
def post(run_id):
    if not _allowed(): return {'error':'forbidden'},403
    try: post_payroll(run_id,current_user.id)
    except ValueError as exc:
        db.session.rollback()
        return {'error':str(exc)},400
    return redirect(url_for('payroll.ui'))

@bp.get('/api')
@login_required
def api():
    return jsonify([{'id':r.id,'period':r.period_name,'status':r.status,'net':str(r.total_net)} for r in PayrollRun.query.order_by(PayrollRun.id.desc()).limit(24).all()])
