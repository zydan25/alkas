from flask import Blueprint, jsonify
from .models import Tournament, Match

bp = Blueprint("tournaments", __name__, url_prefix="/admin/tournaments")

@bp.get("")
def index():
    tournaments = Tournament.query.order_by(Tournament.id.desc()).limit(40).all()
    return jsonify({
        "active": Tournament.query.filter(Tournament.status.in_(["published","live"])).count(),
        "matches": Match.query.filter_by(status="scheduled").count(),
        "items": [{"id": t.id, "name_ar": t.name_ar, "status": t.status} for t in tournaments],
    })
