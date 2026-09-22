from datetime import date
from uuid import uuid4

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from .models import Account, AccountingVoucher, Branch, FiscalPeriod, JournalEntry, JournalLine
from .services import create_account, create_voucher, get_postable_accounts, post_entry

bp = Blueprint("accounting", __name__, url_prefix="/admin/accounting", template_folder="templates")


def _view():
    return current_user.username == "admin" or current_user.has_permission("accounting.view")


def _manage():
    return current_user.username == "admin" or current_user.has_permission("accounting.journal.create")


def _branch_manage():
    return current_user.username == "admin" or current_user.has_permission("closing.manage")


def _context():
    branches = Branch.query.filter_by(is_active=True).order_by(Branch.code).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    leaves = get_postable_accounts()
    return branches, accounts, leaves


@bp.get("")
@login_required
def ui():
    if not _view():
        return {"error": "forbidden"}, 403
    roots = Account.query.filter_by(parent_id=None, is_active=True).order_by(Account.code).all()
    entries = JournalEntry.query.order_by(JournalEntry.id.desc()).limit(40).all()
    vouchers = AccountingVoucher.query.order_by(AccountingVoucher.id.desc()).limit(30).all()
    open_periods = FiscalPeriod.query.filter_by(status="open").order_by(FiscalPeriod.starts_on).all()
    branches, accounts, leaves = _context()
    return render_template(
        "accounting/index.html",
        roots=roots, entries=entries, vouchers=vouchers, open_periods=open_periods,
        branches=branches, leaf_accounts=leaves, all_accounts=accounts,
    )


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
        return render_template(
            "accounting/account_form.html",
            accounts=Account.query.filter_by(is_active=True).order_by(Account.code).all(),
            error=str(exc),
        ), 400
    return redirect(url_for("accounting.ui"))


@bp.get("/journal/new")
@login_required
def journal_new():
    if not _manage():
        return {"error": "forbidden"}, 403
    branches, _, leaves = _context()
    return render_template("accounting/journal_form.html", accounts=leaves, branches=branches, today=date.today())


@bp.post("/journal/new")
@login_required
def journal_create():
    if not _manage():
        return {"error": "forbidden"}, 403

    branches, _, leaves = _context()
    try:
        entry_date = date.fromisoformat(request.form["entry_date"])
        branch_id = int(request.form["branch_id"])
        account_ids = request.form.getlist("line_account")
        debits = request.form.getlist("line_debit")
        credits = request.form.getlist("line_credit")

        if len(account_ids) < 2 or len(account_ids) != len(debits) or len(account_ids) != len(credits):
            raise ValueError("القيد يحتاج إلى سطرين متوازنين على الأقل")

        lines = []
        for account_id, debit, credit in zip(account_ids, debits, credits):
            lines.append({
                "account_id": int(account_id),
                "debit": debit or 0,
                "credit": credit or 0,
            })

        post_entry(
            number=f"JV-MAN-{uuid4().hex[:10].upper()}",
            description_ar=request.form.get("description_ar"),
            entry_date=entry_date,
            lines=lines,
            reference_type="manual",
            user_id=current_user.id,
            branch_id=branch_id,
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template(
            "accounting/journal_form.html",
            accounts=leaves,
            branches=branches,
            today=date.today(),
            error=str(exc),
        ), 400

    return redirect(url_for("accounting.ui"))


@bp.get("/vouchers")
@login_required
def vouchers():
    if not _view():
        return {"error": "forbidden"}, 403
    branches, _, leaves = _context()
    rows = AccountingVoucher.query.order_by(AccountingVoucher.id.desc()).limit(100).all()
    return render_template("accounting/vouchers.html", rows=rows, branches=branches, accounts=leaves)


@bp.post("/vouchers/new")
@login_required
def voucher_create():
    if current_user.username != "admin" and not current_user.has_permission("payment.create"):
        return {"error": "forbidden"}, 403
    try:
        voucher = create_voucher(
            voucher_type=(request.form.get("voucher_type") or "receipt").strip(),
            amount=request.form["amount"],
            from_account_id=int(request.form["from_account_id"]),
            to_account_id=int(request.form["to_account_id"]),
            voucher_date=date.fromisoformat(request.form["voucher_date"]),
            branch_id=int(request.form["branch_id"]),
            reference=request.form.get("reference"),
            description_ar=request.form.get("description_ar"),
            user_id=current_user.id,
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        branches, _, leaves = _context()
        rows = AccountingVoucher.query.order_by(AccountingVoucher.id.desc()).limit(100).all()
        return render_template(
            "accounting/vouchers.html", rows=rows, branches=branches, accounts=leaves, error=str(exc)
        ), 400
    return redirect(url_for("accounting.vouchers"))


@bp.get("/branches")
@login_required
def branches():
    if not _view():
        return {"error": "forbidden"}, 403
    rows = Branch.query.order_by(Branch.is_active.desc(), Branch.code).all()
    return render_template("accounting/branches.html", rows=rows)


@bp.post("/branches/new")
@login_required
def branch_create():
    if not _branch_manage():
        return {"error": "forbidden"}, 403
    code = (request.form.get("code") or "").strip()
    name = (request.form.get("name_ar") or "").strip()
    if not code or not name:
        return render_template("accounting/branches.html", rows=Branch.query.order_by(Branch.code).all(), error="الكود واسم الفرع مطلوبان"), 400
    if Branch.query.filter_by(code=code).first():
        return render_template("accounting/branches.html", rows=Branch.query.order_by(Branch.code).all(), error="كود الفرع مستخدم"), 400
    db.session.add(Branch(code=code, name_ar=name, phone=request.form.get("phone") or None, address_ar=request.form.get("address_ar") or None))
    db.session.commit()
    return redirect(url_for("accounting.branches"))


@bp.post("/branches/<int:branch_id>/toggle")
@login_required
def branch_toggle(branch_id):
    if not _branch_manage():
        return {"error": "forbidden"}, 403
    branch = db.session.get(Branch, branch_id)
    if not branch:
        return {"error": "الفرع غير موجود"}, 404
    if branch.is_active and Branch.query.filter_by(is_active=True).count() <= 1:
        return {"error": "يجب إبقاء فرع محاسبي واحد على الأقل فعالًا"}, 400
    branch.is_active = not branch.is_active
    db.session.commit()
    return redirect(url_for("accounting.branches"))


@bp.get("/api")
@login_required
def api():
    if not _view():
        return jsonify({"error": "forbidden"}), 403
    return jsonify({
        "accounts": Account.query.filter_by(is_active=True).count(),
        "postable_accounts": len(get_postable_accounts()),
        "branches": Branch.query.filter_by(is_active=True).count(),
        "open_periods": FiscalPeriod.query.filter_by(status="open").count(),
        "posted_entries": JournalEntry.query.filter_by(status="posted").count(),
        "vouchers": AccountingVoucher.query.count(),
        "lines": JournalLine.query.count(),
    })


@bp.get("/periods/new")
@login_required
def period_new():
    if current_user.username != "admin" and not current_user.has_permission("closing.manage"):
        return {"error":"forbidden"},403
    return render_template("accounting/period_form.html")


@bp.post("/periods/new")
@login_required
def period_create():
    if current_user.username != "admin" and not current_user.has_permission("closing.manage"):
        return {"error":"forbidden"},403
    try:
        name=(request.form.get("name") or "").strip()
        starts=date.fromisoformat(request.form["starts_on"])
        ends=date.fromisoformat(request.form["ends_on"])
        if not name or ends < starts:
            raise ValueError("بيانات الفترة غير صحيحة")
        if FiscalPeriod.query.filter_by(name=name).first():
            raise ValueError("اسم الفترة مستخدم")
        db.session.add(FiscalPeriod(name=name,starts_on=starts,ends_on=ends,status="open"))
        db.session.commit()
    except (KeyError,TypeError,ValueError) as exc:
        db.session.rollback()
        return render_template("accounting/period_form.html",error=str(exc)),400
    return redirect(url_for("accounting.ui"))


@bp.post("/periods/<int:period_id>/close")
@login_required
def period_close(period_id):
    if current_user.username != "admin" and not current_user.has_permission("closing.manage"):
        return {"error":"forbidden"},403
    period=db.session.get(FiscalPeriod,period_id)
    if not period: return {"error":"الفترة غير موجودة"},404
    if period.status=="closed": return {"error":"الفترة مغلقة مسبقًا"},400
    from datetime import datetime, timezone
    period.status="closed"
    period.closed_at=datetime.now(timezone.utc)
    db.session.commit()
    return redirect(url_for("accounting.ui"))@bp.post('/journal/new')
@login_required
def journal_create():
    if not _manage(): return {'error':'forbidden'},403
    branches, _, leaves = _context()
    try:
        entry_date = date.fromisoformat(request.form['entry_date'])
        branch_id = int(request.form['branch_id'])
        accounts = request.form.getlist('line_account')
        debits = request.form.getlist('line_debit')
        credits = request.form.getlist('line_credit')
        if len(accounts) < 2 or len(accounts) != len(debits) or len(accounts) != len(credits):
            raise ValueError('القيد يحتاج سطرين متوازنين على الأقل')
        lines=[]
        for account_id,debit,credit in zip(accounts,debits,credits):
            lines.append({'account_id':int(account_id),'debit':debit or 0,'credit':credit or 0})
        entry = post_entry(
            number=f'JV-MAN-{uuid4().hex[:10].upper()}',
            description_ar=request.form.get('description_ar'),
            entry_date=entry_date,
            lines=lines,
            reference_type='manual',
            user_id=current_user.id,
            branch_id=branch_id,
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template('accounting/journal_form.html',accounts=leaves,branches=branches,today=date.today(),error=str(exc)),400
    return redirect(url_for('accounting.ui'))



@bp.get('/cost-centers')
@login_required
def cost_centers():
    if not _view(): return {'error':'forbidden'},403
    from .models import CostCenter
    rows=CostCenter.query.order_by(CostCenter.code).all()
    return render_template('accounting/cost_centers.html',rows=rows)

@bp.post('/cost-centers/new')
@login_required
def cost_center_create():
    if not _manage(): return {'error':'forbidden'},403
    from .models import CostCenter
    code=(request.form.get('code') or '').strip(); name=(request.form.get('name_ar') or '').strip()
    if not code or not name: return {'error':'الكود واسم مركز التكلفة مطلوبان'},400
    if CostCenter.query.filter_by(code=code).first(): return {'error':'كود مركز التكلفة مستخدم'},400
    db.session.add(CostCenter(code=code,name_ar=name)); db.session.commit()
    return redirect(url_for('accounting.cost_centers'))
