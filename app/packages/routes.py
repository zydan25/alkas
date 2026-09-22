from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..customers.models import Customer
from ..extensions import db
from .models import BookingPackage, CustomerPackage
bp=Blueprint('packages',__name__,url_prefix='/admin/packages',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('package.manage')
@bp.get('')
@login_required
def ui(): return render_template('packages/index.html',plans=BookingPackage.query.filter_by(is_active=True).order_by(BookingPackage.id.desc()).all(),balances=CustomerPackage.query.filter_by(status='active').order_by(CustomerPackage.id.desc()).limit(80).all(),customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(500).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('packages/form.html',customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        name=(request.form.get('name_ar') or '').strip(); units=request.form.get('total_units') or 0; price=request.form.get('price') or 0
        if not name: raise ValueError('اسم الباقة مطلوب')
        if BookingPackage.query.filter_by(name_ar=name).first(): raise ValueError('الباقة موجودة')
        db.session.add(BookingPackage(name_ar=name,total_units=units,price=price,unit_name_ar=request.form.get('unit_name_ar') or 'ساعة',duration_days=int(request.form['duration_days']) if request.form.get('duration_days') else None))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return render_template('packages/form.html',customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).all(),error=str(exc)),400
    return redirect(url_for('packages.ui'))
@bp.post('/assign')
@login_required
def assign():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        pkg=db.session.get(BookingPackage,int(request.form['package_id'])); cust=db.session.get(Customer,int(request.form['customer_id']))
        if not pkg or not cust: raise ValueError('العميل أو الباقة غير موجودة')
        units=request.form.get('purchased_units') or pkg.total_units
        db.session.add(CustomerPackage(customer_id=cust.id,package_id=pkg.id,purchased_units=units,remaining_units=units,status='active'))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback(); return {'error':str(exc)},400
    return redirect(url_for('packages.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'packages':BookingPackage.query.filter_by(is_active=True).count(),'customer_balances':CustomerPackage.query.filter_by(status='active').count()})