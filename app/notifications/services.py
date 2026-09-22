from datetime import datetime, timezone
from ..extensions import db
from ..realtime import emit_notification_event
from .models import Notification

def notify_user(user_id, title_ar, body_ar, kind="system", priority="normal"):
    row = Notification(user_id=user_id, title_ar=title_ar, body_ar=body_ar, kind=kind, priority=priority)
    db.session.add(row)
    db.session.flush()
    emit_notification_event(user_id, title_ar, body_ar)
    return row
