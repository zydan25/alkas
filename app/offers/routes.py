from flask import Blueprint, jsonify
from .models import Offer

bp = Blueprint("offers", __name__, url_prefix="/admin/offers")

@bp.get("")
def index():
    rows = Offer.query.order_by(Offer.priority.desc(), Offer.id.desc()).limit(50).all()
    return jsonify([{"id": o.id, "title_ar": o.title_ar, "status": o.status, "discount": str(o.discount_percent or 0)} for o in rows])
