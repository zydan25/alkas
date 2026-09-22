from datetime import datetime, timezone
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from ..extensions import db
from .models import NewsCategory, Post
bp=Blueprint('news',__name__,url_prefix='/admin/news',template_folder='templates')
def _allowed(): return current_user.username=='admin' or current_user.has_permission('content.manage')
@bp.get('')
@login_required
def ui(): return render_template('news/index.html',rows=Post.query.order_by(Post.id.desc()).limit(100).all(),categories=NewsCategory.query.filter_by(is_active=True).all())
@bp.get('/new')
@login_required
def new():
    if not _allowed(): return {'error':'forbidden'},403
    return render_template('news/form.html',categories=NewsCategory.query.filter_by(is_active=True).all())
@bp.post('/new')
@login_required
def create():
    if not _allowed(): return {'error':'forbidden'},403
    try:
        title=(request.form.get('title_ar') or '').strip()
        if not title: raise ValueError('عنوان الخبر مطلوب')
        status=request.form.get('status','draft')
        post=Post(category_id=int(request.form['category_id']) if request.form.get('category_id') else None,title_ar=title,summary_ar=request.form.get('summary_ar'),body_ar=request.form.get('body_ar'),cover_url=request.form.get('cover_url'),author_id=current_user.id,status=status,published_at=datetime.now(timezone.utc) if status=='published' else None)
        db.session.add(post);db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback();return render_template('news/form.html',categories=NewsCategory.query.filter_by(is_active=True).all(),error=str(exc)),400
    return redirect(url_for('news.ui'))
@bp.post('/category')
@login_required
def category_create():
    if not _allowed(): return {'error':'forbidden'},403
    name=(request.form.get('name_ar') or '').strip()
    if not name:return {'error':'اسم التصنيف مطلوب'},400
    if NewsCategory.query.filter_by(name_ar=name).first():return {'error':'التصنيف موجود'},400
    db.session.add(NewsCategory(name_ar=name));db.session.commit();return redirect(url_for('news.ui'))
@bp.get('/api')
@login_required
def api(): return jsonify([{'id':r.id,'title_ar':r.title_ar,'status':r.status} for r in Post.query.order_by(Post.id.desc()).limit(50).all()])