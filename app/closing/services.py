from datetime import datetime, timezone
from ..extensions import db
from .models import FinancialClose

def close_day(close_date, expected_cash, actual_cash, user_id=None):
    row = FinancialClose.query.filter_by(close_date=close_date).first()
    if row and row.status == "closed":
        raise ValueError("اليوم مغلق ماليًا")
    if not row:
        row = FinancialClose(close_date=close_date)
        db.session.add(row)
    row.expected_cash = expected_cash
    row.actual_cash = actual_cash
    row.difference = actual_cash - expected_cash
    row.status = "closed"
    row.closed_by_id = user_id
    row.closed_at = datetime.now(timezone.utc)
    db.session.commit()
    return row
