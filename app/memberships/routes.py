from flask import Blueprint, jsonify
from .models import Membership, MembershipPlan

bp = Blueprint("memberships", __name__, url_prefix="/admin/memberships")

@bp.get("")
def index():
    return jsonify({
        "plans": MembershipPlan.query.filter_by(is_active=True).count(),
        "active": Membership.query.filter_by(status="active").count(),
    })
