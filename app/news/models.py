from datetime import datetime, timezone
from ..extensions import db


class NewsCategory(db.Model):
    __tablename__ = "news_categories"
    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(120), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Post(db.Model):
    __tablename__ = "news_posts"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("news_categories.id", ondelete="SET NULL"))
    title_ar = db.Column(db.String(240), nullable=False)
    summary_ar = db.Column(db.String(500))
    body_ar = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    status = db.Column(db.String(30), nullable=False, default="draft")
    published_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PostTag(db.Model):
    __tablename__ = "news_post_tags"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("news_posts.id", ondelete="CASCADE"), nullable=False)
    tag = db.Column(db.String(80), nullable=False, index=True)
