from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..realtime import emit_public_event
from ..utils.media import save_uploaded_media
from .models import AnnouncementCard

bp = Blueprint("announcements", __name__, url_prefix="/admin/announcements", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("settings.manage")


@bp.get("")
@login_required
def ui():
    rows = AnnouncementCard.query.order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()
    ).limit(100).all()
    return render_template("announcements/index.html", rows=rows)


@bp.get("/api")
@login_required
def api():
    now = datetime.now(timezone.utc)
    rows = AnnouncementCard.query.order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()
    ).all()
    rows = [row for row in rows if row.visible(now)]
    return jsonify(
        [
            {
                "id": row.id,
                "title_ar": row.title_ar,
                "type": row.card_type,
                "status": row.status,
                "priority": row.priority,
                "target_url": row.target_url,
            }
            for row in rows[:100]
        ]
    )


@bp.post("/create")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403

    tz = ZoneInfo("Asia/Aden")

    def parse_dt(value):
        value = (value or "").strip()
        if not value:
            return None
        return datetime.fromisoformat(value).replace(tzinfo=tz)

    try:
        card_type = request.form.get("card_type") or "text"
        image_url = save_uploaded_media(request.files.get("image"), "announcements", "image")
        video_url = save_uploaded_media(request.files.get("video"), "announcements", "video")

        if card_type == "image" and not image_url:
            raise ValueError("ارفع صورة لهذه البطاقة.")
        if card_type == "video" and not video_url:
            raise ValueError("ارفع فيديو لهذه البطاقة.")
        if card_type not in {"image", "video"}:
            image_url = None
            video_url = None
        elif image_url and video_url:
            raise ValueError("اختر صورة أو فيديو واحدًا.")

        row = AnnouncementCard(
            title_ar=(request.form.get("title_ar") or "").strip(),
            body_ar=(request.form.get("body_ar") or "").strip(),
            card_type=card_type,
            image_url=image_url,
            video_url=video_url,
            target_url=request.form.get("target_url") or None,
            button_text_ar=request.form.get("button_text_ar") or "عرض التفاصيل",
            accent_label_ar=request.form.get("accent_label_ar") or None,
            status="published",
            priority=int(request.form.get("priority") or 0),
            starts_at=parse_dt(request.form.get("starts_at")),
            ends_at=parse_dt(request.form.get("ends_at")),
        )
        if not row.title_ar:
            raise ValueError("العنوان مطلوب")
        db.session.add(row)
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template(
            "announcements/index.html",
            rows=AnnouncementCard.query.order_by(
                AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()
            ).limit(100).all(),
            error=str(exc),
        ), 400

    emit_public_event("announcement", {"id": row.id, "title_ar": row.title_ar, "type": row.card_type})
    return render_template(
        "announcements/index.html",
        rows=AnnouncementCard.query.order_by(
            AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()
        ).limit(100).all(),
        success="تمت إضافة البطاقة",
    )
