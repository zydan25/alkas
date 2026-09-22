from datetime import date
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import Supplier, PurchaseInvoice, SupplierPayment
bp=Blueprint('suppliers',__name__,url_prefix='/admin/suppliers',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('supplier.manage')
@bp.get('')
@login_required
def ui(): return render_template('suppliers/index.html',suppliers=Supplier.query.filter_by(is_active=True).order_by(Supplier.id.desc()).all(),invoices=PurchaseInvoice.query.order_by(PurchaseInvoice.id.desc()).limit(70).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('suppliers/form.html')
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        code=(request.form.get('code') or '').strip(); name=(request.form.get('name_ar') or '').strip()
        if not code or not name: raise ValueError('كود واسم المورد مطلوبان')
        if Supplier.query.filter_by(code=code).first(): raise ValueError('كود المورد مستخدم')
        db.session.add(Supplier(code=code,name_ar=name,phone=request.form.get('phone'),address_ar=request.form.get('address_ar')));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('suppliers/form.html',error=str(exc)),400
    return redirect(url_for('suppliers.ui'))
@bp.get('/invoice/new')
@login_required
def invoice_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('suppliers/invoice_form.html',suppliers=Supplier.query.filter_by(is_active=True).order_by(Supplier.name_ar).all())

@bp.post('/invoice')
@login_required
def invoice_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        sup=db.session.get(Supplier,int(request.form['supplier_id'])); total=float(request.form['total'])
        if not sup or total<=0: raise ValueError('بيانات فاتورة الشراء غير صحيحة')
        row=PurchaseInvoice(number=(request.form.get('number') or f'PINV-{PurchaseInvoice.query.count()+1:06d}'),supplier_id=sup.id,issue_date=date.fromisoformat(request.form.get('issue_date') or date.today().isoformat()),total=total,paid_amount=0,status='open')
        db.session.add(row); sup.payable_balance=float(sup.payable_balance or 0)+total; db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('suppliers.ui'))
@bp.post('/payment')
@login_required
def payment_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        sup=db.session.get(Supplier,int(request.form['supplier_id'])); amount=float(request.form['amount'])
        if not sup or amount<=0: raise ValueError('بيانات الدفع غير صحيحة')
        inv=db.session.get(PurchaseInvoice,int(request.form['purchase_invoice_id'])) if request.form.get('purchase_invoice_id') else None
        if inv and amount>float(inv.total-inv.paid_amount): raise ValueError('المبلغ أكبر من رصيد الفاتورة')
        db.session.add(SupplierPayment(supplier_id=sup.id,purchase_invoice_id=inv.id if inv else None,amount=amount,method=request.form.get('method','cash')))
        if inv: inv.paid_amount=float(inv.paid_amount or 0)+amount; inv.status='paid' if inv.paid_amount>=inv.total else 'partially_paid'
        sup.payable_balance=max(0,float(sup.payable_balance or 0)-amount); db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('suppliers.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'suppliers':Supplier.query.filter_by(is_active=True).count(),'purchase_invoices':PurchaseInvoice.query.count(),'payables':str(sum((s.payable_balance or 0) for s in Supplier.query.filter_by(is_active=True).all()))})