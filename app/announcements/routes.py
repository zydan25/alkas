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
    return current_user.username == "admin" or current_user.has_permission("content.manage")


def _rows():
    return AnnouncementCard.query.order_by(
        AnnouncementCard.priority.desc(), AnnouncementCard.id.desc()
    ).limit(100).all()


def _parse_dt(value):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("Asia/Aden"))


def _rotation(value):
    try:
        return max(3, min(60, int(value or 6)))
    except (TypeError, ValueError):
        raise ValueError("مدة العرض يجب أن تكون رقمًا بين 3 و60 ثانية.")


def _render_index(error=None, success=None, edit_row=None):
    return render_template(
        "announcements/index.html",
        rows=_rows(),
        error=error,
        success=success,
        edit_row=edit_row,
    )


def _media_values(card_type, old_image=None, old_video=None):
    image_file = request.files.get("image")
    video_file = request.files.get("video")
    has_image = bool(image_file and getattr(image_file, "filename", ""))
    has_video = bool(video_file and getattr(video_file, "filename", ""))

    if has_image and has_video:
        raise ValueError("اختر صورة أو فيديو واحدًا فقط.")

    if card_type == "image":
        image_url = save_uploaded_media(image_file, "announcements", "image") if has_image else old_image
        if not image_url:
            raise ValueError("ارفع صورة لهذه البطاقة.")
        return image_url, None

    if card_type == "video":
        video_url = save_uploaded_media(video_file, "announcements", "video") if has_video else old_video
        if not video_url:
            raise ValueError("ارفع فيديو لهذه البطاقة.")
        return None, video_url

    return None, None


@bp.get("")
@login_required
def ui():
    return _render_index()


@bp.get("/api")
@login_required
def api():
    now = datetime.now(timezone.utc)
    rows = [row for row in _rows() if row.visible(now)]
    return jsonify(
        [
            {
                "id": row.id,
                "title_ar": row.title_ar,
                "type": row.card_type,
                "status": row.status,
                "priority": row.priority,
                "image_url": row.image_url,
                "video_url": row.video_url,
                "target_url": row.target_url,
                "rotation_seconds": row.rotation_seconds,
            }
            for row in rows
        ]
    )


@bp.post("/create")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403

    try:
        card_type = (request.form.get("card_type") or "text").strip()
        if card_type not in {"text", "temporary", "image", "video", "link"}:
            raise ValueError("نوع البطاقة غير مدعوم.")

        title = (request.form.get("title_ar") or "").strip()
        if not title:
            raise ValueError("العنوان مطلوب.")

        starts_at = _parse_dt(request.form.get("starts_at"))
        ends_at = _parse_dt(request.form.get("ends_at"))
        if starts_at and ends_at and ends_at <= starts_at:
            raise ValueError("وقت نهاية الظهور يجب أن يكون بعد وقت البداية.")

        image_url, video_url = _media_values(card_type)
        status = request.form.get("status", "published")
        if status not in {"draft", "published", "paused"}:
            status = "published"

        row = AnnouncementCard(
            title_ar=title,
            body_ar=(request.form.get("body_ar") or "").strip() or None,
            card_type=card_type,
            image_url=image_url,
            video_url=video_url,
            target_url=(request.form.get("target_url") or "").strip() or None,
            button_text_ar=(request.form.get("button_text_ar") or "عرض التفاصيل").strip(),
            accent_label_ar=(request.form.get("accent_label_ar") or "").strip() or None,
            status=status,
            priority=int(request.form.get("priority") or 0),
            rotation_seconds=_rotation(request.form.get("rotation_seconds")),
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db.session.add(row)
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return _render_index(error=str(exc)), 400

    emit_public_event(
        "announcement",
        {
            "id": row.id,
            "title_ar": row.title_ar,
            "type": row.card_type,
            "rotation_seconds": row.rotation_seconds,
        },
    )
    return _render_index(success="تم نشر البطاقة بنجاح.")


@bp.get("/<int:card_id>/edit")
@login_required
def edit(card_id):
    if not _allowed():
        return {"error": "forbidden"}, 403
    row = AnnouncementCard.query.get_or_404(card_id)
    return _render_index(edit_row=row)


@bp.post("/<int:card_id>/edit")
@login_required
def edit_post(card_id):
    if not _allowed():
        return {"error": "forbidden"}, 403

    row = AnnouncementCard.query.get_or_404(card_id)
    try:
        card_type = (request.form.get("card_type") or "text").strip()
        if card_type not in {"text", "temporary", "image", "video", "link"}:
            raise ValueError("نوع البطاقة غير مدعوم.")

        title = (request.form.get("title_ar") or "").strip()
        if not title:
            raise ValueError("العنوان مطلوب.")

        starts_at = _parse_dt(request.form.get("starts_at"))
        ends_at = _parse_dt(request.form.get("ends_at"))
        if starts_at and ends_at and ends_at <= starts_at:
            raise ValueError("وقت نهاية الظهور يجب أن يكون بعد وقت البداية.")

        image_url, video_url = _media_values(card_type, row.image_url, row.video_url)
        status = request.form.get("status", "published")
        if status not in {"draft", "published", "paused"}:
            status = "published"

        row.title_ar = title
        row.body_ar = (request.form.get("body_ar") or "").strip() or None
        row.card_type = card_type
        row.image_url = image_url
        row.video_url = video_url
        row.target_url = (request.form.get("target_url") or "").strip() or None
        row.button_text_ar = (request.form.get("button_text_ar") or "عرض التفاصيل").strip()
        row.accent_label_ar = (request.form.get("accent_label_ar") or "").strip() or None
        row.status = status
        row.priority = int(request.form.get("priority") or 0)
        row.rotation_seconds = _rotation(request.form.get("rotation_seconds"))
        row.starts_at = starts_at
        row.ends_at = ends_at
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return _render_index(error=str(exc), edit_row=row), 400

    emit_public_event(
        "announcement",
        {
            "id": row.id,
            "title_ar": row.title_ar,
            "type": row.card_type,
            "rotation_seconds": row.rotation_seconds,
        },
    )
    return _render_index(success="تم تحديث البطاقة.")


@bp.post("/<int:card_id>/toggle")
@login_required
def toggle(card_id):
    if not _allowed():
        return {"error": "forbidden"}, 403
    row = AnnouncementCard.query.get_or_404(card_id)
    row.status = "paused" if row.status == "published" else "published"
    db.session.commit()
    emit_public_event(
        "announcement",
        {"id": row.id, "title_ar": row.title_ar, "type": row.card_type},
    )
    return _render_index(success="تم " + ("إيقاف" if row.status == "paused" else "تفعيل") + " البطاقة.")


@bp.post("/<int:card_id>/delete")
@login_required
def delete(card_id):
    if not _allowed():
        return {"error": "forbidden"}, 403
    row = AnnouncementCard.query.get_or_404(card_id)
    db.session.delete(row)
    db.session.commit()
    emit_public_event("announcement", {"id": row.id, "deleted": True})
    return _render_index(success="تم حذف البطاقة.")
