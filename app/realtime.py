from flask_login import current_user
from flask_socketio import join_room

from .extensions import socketio


@socketio.on("connect")
def handle_connect():
    join_room("public")
    if not current_user.is_authenticated:
        return
    join_room(f"user:{current_user.id}")
    if current_user.has_permission("booking.view") or current_user.username == "admin":
        join_room("operations")


def emit_booking_event(event_name, booking):
    socketio.emit(
        "booking",
        {
            "event": event_name,
            "booking_id": booking.id,
            "booking_number": booking.booking_number,
            "status": booking.status,
            "payment_status": booking.payment_status,
        },
        to="operations",
        namespace="/",
    )


def emit_notification_event(user_id, title_ar, body_ar):
    socketio.emit(
        "notification",
        {"title_ar": title_ar, "body_ar": body_ar},
        to=f"user:{user_id}",
        namespace="/",
    )


def emit_public_event(event_name, payload=None):
    socketio.emit(
        event_name,
        payload or {},
        to="public",
        namespace="/",
    )
