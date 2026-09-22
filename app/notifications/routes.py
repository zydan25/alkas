from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from .models import Notification

bp = Blueprint("notifications", __name__, url_prefix="/notifications")

@bp.get("")
@login_required
def index():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(50).all()
    return jsonify([{"id": n.id, "title_ar": n.title_ar, "body_ar": n.body_ar, "read": n.is_read, "kind": n.kind} for n in rows])
