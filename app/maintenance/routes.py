from flask import Blueprint, jsonify
from .models import MaintenanceRequest

bp = Blueprint("maintenance", __name__, url_prefix="/admin/maintenance")

@bp.get("")
def index():
    rows = MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(50).all()
    return jsonify([{
        "id": r.id, "resource_id": r.resource_id, "title_ar": r.title_ar,
        "priority": r.priority, "status": r.status
    } for r in rows])
