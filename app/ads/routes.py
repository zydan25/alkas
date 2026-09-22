from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import AdCampaign, AdCreative

bp = Blueprint("ads", __name__, url_prefix="/admin/ads")

@bp.get("")
@login_required
def ui():
    campaigns = AdCampaign.query.order_by(AdCampaign.id.desc()).limit(70).all()
    creatives = AdCreative.query.order_by(AdCreative.id.desc()).limit(70).all()
    return render_template("ads/index.html", campaigns=campaigns, creatives=creatives)

@bp.get("/api")
@login_required
def api():
    return jsonify({"campaigns": AdCampaign.query.filter_by(status="active").count(), "creatives": AdCreative.query.filter_by(status="active").count()})
