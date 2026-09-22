from flask import Blueprint, render_template
from flask_login import current_user, login_required
from .models import AuditLog
bp=Blueprint("audit",__name__,url_prefix="/admin/audit",template_folder="templates")
@bp.get("")
@login_required
def ui():
    if current_user.username!="admin" and not current_user.has_permission("audit.view"):
        return {"error":"forbidden"},403
    return render_template("audit/index.html",rows=AuditLog.query.order_by(AuditLog.id.desc()).limit(200).all())
