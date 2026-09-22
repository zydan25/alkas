from flask import Blueprint, jsonify
from .models import AdCampaign, AdCreative

bp = Blueprint("ads", __name__, url_prefix="/admin/ads")

@bp.get("")
def index():
    return jsonify({
        "campaigns": AdCampaign.query.filter_by(status="active").count(),
        "creatives": AdCreative.query.filter_by(status="active").count(),
    })
