from datetime import time
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from .models import PriceOverride, PriceRule

bp=Blueprint("pricing",__name__,url_prefix="/admin/pricing",template_folder="templates")

def _allowed(): return current_user.username=="admin" or current_user.has_permission("pricing.manage")

@bp.get("")
@login_required
def ui():
    return render_template("pricing/index.html",rules=PriceRule.query.filter_by(is_active=True).order_by(PriceRule.priority.desc(),PriceRule.id.desc()).limit(100).all(),overrides=PriceOverride.query.filter_by(is_active=True).order_by(PriceOverride.id.desc()).limit(50).all())

@bp.get("/new")
@login_required
def new():
    if not _allowed(): return {"error":"forbidden"},403
    return render_template("pricing/form.html")

@bp.post("/new")
@login_required
def create():
    if not _allowed(): return {"error":"forbidden"},403
    try:
        rule=PriceRule(
            name_ar=(request.form.get("name_ar") or "").strip(),
            price_per_hour=request.form["price_per_hour"],
            weekday=(int(request.form["weekday"]) if request.form.get("weekday") else None),
            start_time=(time.fromisoformat(request.form["start_time"]) if request.form.get("start_time") else None),
            end_time=(time.fromisoformat(request.form["end_time"]) if request.form.get("end_time") else None),
            min_minutes=(int(request.form["min_minutes"]) if request.form.get("min_minutes") else None),
            max_minutes=(int(request.form["max_minutes"]) if request.form.get("max_minutes") else None),
            priority=int(request.form.get("priority") or 0),
        )
    except (KeyError,TypeError,ValueError) as exc:
        return render_template("pricing/form.html",error="بيانات القاعدة غير صحيحة: "+str(exc)),400
    if not rule.name_ar: return render_template("pricing/form.html",error="اسم القاعدة مطلوب"),400
    db.session.add(rule)
    db.session.commit()
    return redirect(url_for("pricing.ui"))

@bp.get("/api")
@login_required
def api():
    return jsonify({"rules":PriceRule.query.filter_by(is_active=True).count(),"overrides":PriceOverride.query.filter_by(is_active=True).count()})
