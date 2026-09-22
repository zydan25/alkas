from datetime import date, timedelta
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..customers.models import Customer
from ..extensions import db
from .models import Membership, MembershipPlan
bp=Blueprint('memberships',__name__,url_prefix='/admin/memberships',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('membership.manage')
@bp.get('')
@login_required
def ui():
    return render_template('memberships/index.html',plans=MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.id.desc()).all(),memberships=Membership.query.order_by(Membership.id.desc()).limit(80).all(),customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(500).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('memberships/form.html',customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip(); price=request.form.get('price') or 0; days=int(request.form.get('duration_days') or 30)
        if not name: raise ValueError('اسم الخطة مطلوب')
        if days<=0: raise ValueError('مدة الخطة غير صحيحة')
        if MembershipPlan.query.filter_by(name_ar=name).first(): raise ValueError('الخطة موجودة')
        db.session.add(MembershipPlan(name_ar=name,price=price,discount_percent=request.form.get('discount_percent') or 0,priority_booking=request.form.get('priority_booking')=='1',duration_days=days))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return render_template('memberships/form.html',customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all(),error=str(exc)),400
    return redirect(url_for('memberships.ui'))
@bp.post('/assign')
@login_required
def assign():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        start=date.fromisoformat(request.form.get('starts_on') or date.today().isoformat())
        plan=db.session.get(MembershipPlan,int(request.form['plan_id']))
        customer=db.session.get(Customer,int(request.form['customer_id']))
        if not plan or not customer: raise ValueError('العميل أو الخطة غير موجودة')
        db.session.add(Membership(customer_id=customer.id,plan_id=plan.id,starts_on=start,ends_on=start+timedelta(days=plan.duration_days-1),status='active',auto_renew=request.form.get('auto_renew')=='1'))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return {'error':str(exc)},400
    return redirect(url_for('memberships.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'plans':MembershipPlan.query.filter_by(is_active=True).count(),'active':Membership.query.filter_by(status='active').count()})