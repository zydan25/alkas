from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from .models import Account, FiscalPeriod, JournalEntry, JournalLine

bp = Blueprint("accounting", __name__, url_prefix="/admin/accounting")


def _allowed():
    return current_user.has_permission("accounting.view") or current_user.username == "admin"


@bp.get("")
@login_required
def ui():
    if not _allowed():
        return {"error": "forbidden"}, 403
    roots = Account.query.filter_by(parent_id=None, is_active=True).order_by(Account.code).all()
    entries = JournalEntry.query.order_by(JournalEntry.id.desc()).limit(25).all()
    return render_template("accounting/index.html", roots=roots, entries=entries)


@bp.get("/api")
@login_required
def api():
    if not _allowed():
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "accounts": Account.query.filter_by(is_active=True).count(),
        "open_periods": FiscalPeriod.query.filter_by(status="open").count(),
        "posted_entries": JournalEntry.query.filter_by(status="posted").count(),
        "lines": JournalLine.query.count(),
        "recent_entries": [
            {"number": e.number, "date": e.entry_date.isoformat(), "description_ar": e.description_ar}
            for e in JournalEntry.query.order_by(JournalEntry.id.desc()).limit(20).all()
        ],
    })
