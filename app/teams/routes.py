from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Team, Player
bp=Blueprint("teams",__name__,url_prefix="/admin/teams")
@bp.get("")
@login_required
def ui():
    return render_template("teams/index.html",teams=Team.query.filter_by(is_active=True).order_by(Team.id.desc()).all(),players=Player.query.filter_by(is_active=True).order_by(Player.id.desc()).limit(80).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"teams":Team.query.filter_by(is_active=True).count(),"players":Player.query.filter_by(is_active=True).count()})