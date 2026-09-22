from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import PriceOverride, PriceRule
bp=Blueprint("pricing",__name__,url_prefix="/admin/pricing",template_folder="templates")

@bp.get("")
@login_required
def ui():
    return render_template("pricing/index.html",rules=PriceRule.query.filter_by(is_active=True).order_by(PriceRule.priority.desc(),PriceRule.id.desc()).limit(100).all(),overrides=PriceOverride.query.filter_by(is_active=True).order_by(PriceOverride.id.desc()).limit(50).all())

@bp.get("/api")
@login_required
def api():
    return jsonify({"rules":PriceRule.query.filter_by(is_active=True).count(),"overrides":PriceOverride.query.filter_by(is_active=True).count()})
