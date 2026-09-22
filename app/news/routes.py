from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Post, NewsCategory
bp=Blueprint("news",__name__,url_prefix="/admin/news",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("news/index.html",rows=Post.query.order_by(Post.id.desc()).limit(100).all(),categories=NewsCategory.query.filter_by(is_active=True).all())
@bp.get("/api")
@login_required
def api():
    rows=Post.query.filter_by(status="published").order_by(Post.published_at.desc()).limit(30).all()
    return jsonify([{"id":p.id,"title_ar":p.title_ar,"summary_ar":p.summary_ar,"status":p.status} for p in rows])