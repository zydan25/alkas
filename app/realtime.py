from .extensions import socketio


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
        namespace="/",
    )


def emit_notification_event(user_id, title_ar, body_ar):
    socketio.emit(
        "notification",
        {"user_id": user_id, "title_ar": title_ar, "body_ar": body_ar},
        namespace="/",
    )
