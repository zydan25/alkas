from datetime import datetime, timezone
from flask import Blueprint, jsonify
from .models import Post

bp = Blueprint("news", __name__, url_prefix="/admin/news")

@bp.get("")
def index():
    rows = Post.query.filter_by(status="published").order_by(Post.published_at.desc()).limit(30).all()
    return jsonify([{"id": p.id, "title_ar": p.title_ar, "summary_ar": p.summary_ar, "cover_url": p.cover_url} for p in rows])
