from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template

from ..models import Announcement, Resource, Sport

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    now = datetime.now(timezone.utc)
    announcements = (
        Announcement.query
        .filter(Announcement.status == "published")
        .order_by(Announcement.priority.desc(), Announcement.created_at.desc())
        .all()
    )
    announcements = [item for item in announcements if item.is_visible_now(now)][:6]
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    resources = Resource.query.filter_by(is_active=True).limit(8).all()
    return render_template("public/home.html", announcements=announcements, sports=sports, resources=resources)


@bp.get("/api/sports")
def api_sports():
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all()
    return jsonify([
        {"id": s.id, "key": s.key, "name_ar": s.name_ar, "icon": s.icon}
        for s in sports
    ])
