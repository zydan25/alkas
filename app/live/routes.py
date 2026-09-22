from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import LiveEvent, Stream
bp=Blueprint("live",__name__,url_prefix="/admin/live",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("live/index.html",events=LiveEvent.query.order_by(LiveEvent.starts_at.desc(),LiveEvent.id.desc()).limit(60).all(),streams=Stream.query.order_by(Stream.id.desc()).limit(60).all())
@bp.get("/api")
@login_required
def api():
    events=LiveEvent.query.order_by(LiveEvent.starts_at.desc()).limit(30).all()
    return jsonify({"live_now":LiveEvent.query.filter_by(status="live").count(),"streams":Stream.query.filter_by(status="live").count(),"events":[{"id":e.id,"name_ar":e.name_ar,"status":e.status} for e in events]})