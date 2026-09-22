from flask import Blueprint, jsonify
from .models import Team, Player

bp = Blueprint("teams", __name__, url_prefix="/admin/teams")

@bp.get("")
def index():
    return jsonify({
        "teams": Team.query.filter_by(is_active=True).count(),
        "players": Player.query.filter_by(is_active=True).count(),
    })
