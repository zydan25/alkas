from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Coupon, Offer
bp=Blueprint("offers",__name__,url_prefix="/admin/offers",template_folder="templates")
@bp.get("")
@login_required
def ui():
    return render_template("offers/index.html",offers=Offer.query.order_by(Offer.priority.desc(),Offer.id.desc()).limit(100).all(),coupons=Coupon.query.order_by(Coupon.id.desc()).limit(80).all())
@bp.get("/api")
@login_required
def api():
    rows=Offer.query.order_by(Offer.priority.desc(),Offer.id.desc()).limit(50).all()
    return jsonify([{"id":o.id,"title_ar":o.title_ar,"status":o.status,"discount":str(o.discount_percent or 0)} for o in rows])