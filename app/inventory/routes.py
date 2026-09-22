from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import Product, ProductCategory, Warehouse, StockMovement
bp=Blueprint('inventory',__name__,url_prefix='/admin/inventory',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('inventory.manage')
@bp.get('')
@login_required
def ui(): return render_template('inventory/index.html',products=Product.query.filter_by(is_active=True).order_by(Product.id.desc()).limit(100).all(),warehouses=Warehouse.query.filter_by(is_active=True).all(),movements=StockMovement.query.order_by(StockMovement.id.desc()).limit(60).all(),categories=ProductCategory.query.order_by(ProductCategory.name_ar).all())
@bp.get('/product/new')
@login_required
def product_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('inventory/product_form.html',categories=ProductCategory.query.order_by(ProductCategory.name_ar).all())
@bp.post('/product/new')
@login_required
def product_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        sku=(request.form.get('sku') or '').strip(); name=(request.form.get('name_ar') or '').strip()
        if not sku or not name: raise ValueError('SKU واسم المنتج مطلوبان')
        if Product.query.filter_by(sku=sku).first(): raise ValueError('SKU مستخدم')
        db.session.add(Product(sku=sku,name_ar=name,category_id=int(request.form['category_id']) if request.form.get('category_id') else None,unit_ar=request.form.get('unit_ar') or 'قطعة',cost_price=request.form.get('cost_price') or 0,sale_price=request.form.get('sale_price') or 0,reorder_level=request.form.get('reorder_level') or 0));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return render_template('inventory/product_form.html',categories=ProductCategory.query.order_by(ProductCategory.name_ar).all(),error=str(exc)),400
    return redirect(url_for('inventory.ui'))
@bp.post('/category')
@login_required
def category_create():
    if not _allowed(): return {'error':'forbidden'},403
    name=(request.form.get('name_ar') or '').strip()
    if not name:return {'error':'اسم التصنيف مطلوب'},400
    db.session.add(ProductCategory(name_ar=name));db.session.commit();return redirect(url_for('inventory.ui'))
@bp.post('/warehouse')
@login_required
def warehouse_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        db.session.add(Warehouse(code=(request.form.get('code') or '').strip(),name_ar=(request.form.get('name_ar') or '').strip()));db.session.commit()
    except Exception as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('inventory.ui'))
@bp.get('/movement/new')
@login_required
def movement_new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('inventory/movement_form.html',products=Product.query.filter_by(is_active=True).order_by(Product.name_ar).all(),warehouses=Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name_ar).all())

@bp.post('/movement')
@login_required
def movement_create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        db.session.add(StockMovement(product_id=int(request.form['product_id']),warehouse_id=int(request.form['warehouse_id']),movement_type=request.form.get('movement_type','in'),quantity=request.form['quantity'],unit_cost=request.form.get('unit_cost') or 0,reference_type='manual'));db.session.commit()
    except (KeyError,TypeError,ValueError) as exc: db.session.rollback();return {'error':str(exc)},400
    return redirect(url_for('inventory.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify({'products':Product.query.filter_by(is_active=True).count(),'warehouses':Warehouse.query.filter_by(is_active=True).count(),'movements':StockMovement.query.count()})