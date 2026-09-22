from datetime import datetime, timezone
from flask import Blueprint, jsonify
from .models import AnnouncementCard

bp = Blueprint("announcements", __name__, url_prefix="/admin/announcements")

@bp.get("")
def index():
    now = datetime.now(timezone.utc)
    rows = AnnouncementCard.query.order_by(AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()).all()
    rows = [row for row in rows if row.visible(now)]
    return jsonify([{
        "id": row.id, "title_ar": row.title_ar, "body_ar": row.body_ar,
        "type": row.card_type, "image_url": row.image_url,
        "video_url": row.video_url, "target_url": row.target_url,
        "accent_label_ar": row.accent_label_ar,
    } for row in rows[:100]])
