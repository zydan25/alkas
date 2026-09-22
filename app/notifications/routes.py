from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from .models import Notification

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.get("")
@login_required
def index():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    return jsonify([{"id": n.id, "title_ar": n.title_ar, "body_ar": n.body_ar, "read": n.is_read, "kind": n.kind, "created_at": n.created_at.isoformat()} for n in rows])


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
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "ok"})
