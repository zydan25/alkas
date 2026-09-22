from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from .models import MaintenanceRequest

bp = Blueprint("maintenance", __name__, url_prefix="/admin/maintenance", template_folder="templates")

@bp.get("")
@login_required
def ui():
    rows = MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(100).all()
    return render_template("maintenance/index.html", rows=rows)

@bp.get("/api")
@login_required
def api():
    rows = MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(50).all()
    return jsonify([{"id": r.id, "resource_id": r.resource_id, "title_ar": r.title_ar, "priority": r.priority, "status": r.status} for r in rows])
