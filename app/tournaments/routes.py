from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Match, Tournament

bp = Blueprint("tournaments", __name__, url_prefix="/admin/tournaments", template_folder="templates")

@bp.get("")
@login_required
def ui():
    tournaments = Tournament.query.order_by(Tournament.id.desc()).limit(60).all()
    matches = Match.query.order_by(Match.starts_at.desc(), Match.id.desc()).limit(60).all()
    return render_template("tournaments/index.html", tournaments=tournaments, matches=matches)

@bp.get("/api")
@login_required
def api():
    tournaments = Tournament.query.order_by(Tournament.id.desc()).limit(40).all()
    return jsonify({
        "active": Tournament.query.filter(Tournament.status.in_(["published","live"])).count(),
        "matches": Match.query.filter_by(status="scheduled").count(),
        "items": [{"id": t.id, "name_ar": t.name_ar, "status": t.status} for t in tournaments],
    })
