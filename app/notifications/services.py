from datetime import datetime, timezone

from ..extensions import db
from ..realtime import emit_notification_event
from .models import Notification, NotificationLog, NotificationPreference


def notify_user(user_id, title_ar, body_ar, kind="system", priority="normal", channels=None):
    notification = Notification(
        user_id=user_id,
        title_ar=title_ar,
        body_ar=body_ar,
        kind=kind,
        priority=priority,
    )
    db.session.add(notification)
    db.session.flush()

    emit_notification_event(user_id, title_ar, body_ar)

    pref = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.session.add(pref)
        db.session.flush()

    requested = channels or ["push", "whatsapp", "email"]
    enabled = {
        "push": pref.push_enabled,
        "whatsapp": pref.whatsapp_enabled,
        "sms": pref.sms_enabled,
        "email": pref.email_enabled,
    }

    for channel in requested:
        if not enabled.get(channel, False):
            continue
        db.session.add(NotificationLog(
            notification_id=notification.id,
            channel=channel,
            status="queued",
        ))

    return notification


def mark_delivered(log_id, provider_message_id=None):
    log = db.session.get(NotificationLog, log_id)
    if not log:
        raise ValueError("سجل التسليم غير موجود")
    log.status = "sent"
    log.provider_message_id = provider_message_id
    log.sent_at = datetime.now(timezone.utc)
    db.session.commit()
    return log


def mark_failed(log_id, reason=None):
    log = db.session.get(NotificationLog, log_id)
    if not log:
        raise ValueError("سجل التسليم غير موجود")
    log.status = "failed"
    log.destination = reason or log.destination
    db.session.commit()
    return log
