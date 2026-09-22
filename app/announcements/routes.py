from datetime import datetime, timezone
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from .models import AnnouncementCard
from ..realtime import emit_public_event

bp = Blueprint("announcements", __name__, url_prefix="/admin/announcements")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("settings.manage")


@bp.get("")
@login_required
def ui():
    rows = AnnouncementCard.query.order_by(AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()).limit(100).all()
    return render_template("announcements/index.html", rows=rows)


@bp.get("/api")
@login_required
def api():
    now = datetime.now(timezone.utc)
    rows = AnnouncementCard.query.order_by(AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()).all()
    rows = [row for row in rows if row.visible(now)]
    return jsonify([{
        "id": row.id, "title_ar": row.title_ar, "type": row.card_type,
        "status": row.status, "priority": row.priority, "target_url": row.target_url
    } for row in rows[:100]])


@bp.post("/create")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    row = AnnouncementCard(
        title_ar=(request.form.get("title_ar") or "").strip(),
        body_ar=(request.form.get("body_ar") or "").strip(),
        card_type=request.form.get("card_type") or "text",
        image_url=request.form.get("image_url") or None,
        video_url=request.form.get("video_url") or None,
        target_url=request.form.get("target_url") or None,
        button_text_ar=request.form.get("button_text_ar") or "عرض التفاصيل",
        accent_label_ar=request.form.get("accent_label_ar") or None,
        status="published",
        priority=int(request.form.get("priority") or 0),
    )
    if not row.title_ar:
        return {"error": "العنوان مطلوب"}, 400
    db.session.add(row)
    db.session.commit()
    emit_public_event("announcement", {"id": row.id, "title_ar": row.title_ar, "type": row.card_type})
    return render_template("announcements/index.html", rows=AnnouncementCard.query.order_by(AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()).limit(100).all(), success="تمت إضافة البطاقة")
