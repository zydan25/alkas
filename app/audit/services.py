from flask import has_request_context, request
from flask_login import current_user
from ..extensions import db
from .models import AuditLog

def record(action, entity_type, entity_id=None, before=None, after=None):
    log=AuditLog(
        actor_id=current_user.id if getattr(current_user,"is_authenticated",False) else None,
        action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None,
        before_json=before, after_json=after,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr) if has_request_context() else None,
        user_agent=request.headers.get("User-Agent") if has_request_context() else None,
    )
    db.session.add(log)
    return log
