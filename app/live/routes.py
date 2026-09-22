from flask import Blueprint, jsonify
from .models import LiveEvent, Stream

bp = Blueprint("live", __name__, url_prefix="/admin/live")

@bp.get("")
def index():
    events = LiveEvent.query.order_by(LiveEvent.starts_at.desc()).limit(30).all()
    return jsonify({
        "live_now": LiveEvent.query.filter_by(status="live").count(),
        "streams": Stream.query.filter_by(status="live").count(),
        "events": [{"id": e.id, "name_ar": e.name_ar, "status": e.status} for e in events],
    })
