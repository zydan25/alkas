from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func

from .models import Account, FiscalPeriod, JournalEntry
from ..extensions import db

bp = Blueprint("accounting", __name__, url_prefix="/admin/accounting")


def _allowed():
    return current_user.has_permission("accounting.view") or current_user.username == "admin"


@bp.get("")
@login_required
def index():
    if not _allowed():
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "accounts": Account.query.filter_by(is_active=True).count(),
        "open_periods": FiscalPeriod.query.filter_by(status="open").count(),
        "posted_entries": JournalEntry.query.filter_by(status="posted").count(),
        "debit_total": str(db.session.query(func.coalesce(func.sum(db.text("0")), 0)).scalar() or 0),
        "recent_entries": [
            {"number": e.number, "date": e.entry_date.isoformat(), "description_ar": e.description_ar}
            for e in JournalEntry.query.order_by(JournalEntry.id.desc()).limit(20).all()
        ],
    })
