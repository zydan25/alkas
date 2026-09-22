from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from ..extensions import db
from .models import Notification

bp = Blueprint("notifications", __name__, url_prefix="/notifications", template_folder="templates")


@bp.get("")
@login_required
def ui():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template("notifications/index.html", notifications=rows, unread=unread)


@bp.post("/preferences")
@login_required
def preferences():
    pref=NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not pref:
        pref=NotificationPreference(user_id=current_user.id)
        db.session.add(pref)
    for field in ("push_enabled","whatsapp_enabled","sms_enabled","email_enabled"):
        setattr(pref,field,request.form.get(field)=="1")
    db.session.commit()
    return redirect(url_for("notifications.ui"))

@bp.get("/api")
@login_required
def api():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    return jsonify([{
        "id": n.id, "title_ar": n.title_ar, "body_ar": n.body_ar, "read": n.is_read,
        "kind": n.kind, "priority": n.priority, "created_at": n.created_at.isoformat(),
    } for n in rows])


@bp.post("/<int:notification_id>/read")
@login_required
def mark_read(notification_id):
    row = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    row.is_read = True
    db.session.commit()
    return jsonify({"id": row.id, "read": True})


@bp.post("/read-all")
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {Notification.is_read: True}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({"status": "ok"})
