from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from .models import Membership, MembershipPlan
bp=Blueprint("memberships",__name__,url_prefix="/admin/memberships")
@bp.get("")
@login_required
def ui():
    return render_template("memberships/index.html", plans=MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.id.desc()).all(), memberships=Membership.query.order_by(Membership.id.desc()).limit(80).all())
@bp.get("/api")
@login_required
def api():
    return jsonify({"plans":MembershipPlan.query.filter_by(is_active=True).count(),"active":Membership.query.filter_by(status="active").count()})