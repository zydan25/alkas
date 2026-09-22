from datetime import date
from uuid import uuid4

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from .models import Account, FiscalPeriod, JournalEntry, JournalLine
from .services import create_account, post_entry

bp = Blueprint("accounting", __name__, url_prefix="/admin/accounting", template_folder="templates")


def _view():
    return current_user.username == "admin" or current_user.has_permission("accounting.view")


def _manage():
    return current_user.username == "admin" or current_user.has_permission("accounting.journal.create")


@bp.get("")
@login_required
def ui():
    if not _view():
        return {"error": "forbidden"}, 403
    roots = Account.query.filter_by(parent_id=None, is_active=True).order_by(Account.code).all()
    entries = JournalEntry.query.order_by(JournalEntry.id.desc()).limit(40).all()
    open_periods = FiscalPeriod.query.filter_by(status="open").order_by(FiscalPeriod.starts_on).all()
    return render_template("accounting/index.html", roots=roots, entries=entries, open_periods=open_periods)


@bp.get("/accounts/new")
@login_required
def account_new():
    if not _manage():
        return {"error": "forbidden"}, 403
    return render_template(
        "accounting/account_form.html",
        accounts=Account.query.filter_by(is_active=True).order_by(Account.code).all(),
    )


@bp.post("/accounts/new")
@login_required
def account_create():
    if not _manage():
        return {"error": "forbidden"}, 403
    try:
        account = create_account(
            name_ar=request.form.get("name_ar"),
            account_type=request.form.get("account_type"),
            parent_id=int(request.form["parent_id"]) if request.form.get("parent_id") else None,
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template("accounting/account_form.html", accounts=Account.query.filter_by(is_active=True).order_by(Account.code).all(), error=str(exc)), 400
    return redirect(url_for("accounting.ui"))


@bp.get("/journal/new")
@login_required
def journal_new():
    if not _manage():
        return {"error": "forbidden"}, 403
    return render_template("accounting/journal_form.html", accounts=Account.query.filter_by(is_active=True).order_by(Account.code).all(), today=date.today())


@bp.post("/journal/new")
@login_required
def journal_create():
    if not _manage():
        return {"error": "forbidden"}, 403
    try:
        debit_account = int(request.form["debit_account"])
        credit_account = int(request.form["credit_account"])
        amount = request.form["amount"]
        entry_date = date.fromisoformat(request.form["entry_date"])
        entry = post_entry(
            number=f"JV-MAN-{uuid4().hex[:10].upper()}",
            description_ar=request.form.get("description_ar"),
            entry_date=entry_date,
            lines=[
                {"account_id": debit_account, "debit": amount, "credit": 0},
                {"account_id": credit_account, "debit": 0, "credit": amount},
            ],
            reference_type="manual",
            user_id=current_user.id,
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template("accounting/journal_form.html", accounts=Account.query.filter_by(is_active=True).order_by(Account.code).all(), today=date.today(), error=str(exc)), 400
    return redirect(url_for("accounting.ui"))


@bp.get("/api")
@login_required
def api():
    if not _view():
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "accounts": Account.query.filter_by(is_active=True).count(),
        "open_periods": FiscalPeriod.query.filter_by(status="open").count(),
        "posted_entries": JournalEntry.query.filter_by(status="posted").count(),
        "lines": JournalLine.query.count(),
    })
