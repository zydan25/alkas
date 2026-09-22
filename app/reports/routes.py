from flask import Blueprint, jsonify
from .services import dashboard_snapshot

bp = Blueprint("reports", __name__, url_prefix="/admin/reports")

@bp.get("/dashboard")
def dashboard():
    return jsonify(dashboard_snapshot())

@bp.get("/summary")
def summary():
    return jsonify(dashboard_snapshot())
