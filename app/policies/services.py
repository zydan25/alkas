from datetime import datetime, timezone
from .models import BookingPolicy

def cancellation_refund_percent(policy, start_at, now=None):
    now = now or datetime.now(timezone.utc)
    minutes_left = (start_at - now).total_seconds() / 60
    if minutes_left >= policy.cancellation_deadline_minutes:
        return float(policy.refund_percent_before_deadline)
    return float(policy.refund_percent_after_deadline)
