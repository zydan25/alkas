from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func

from ..audit.services import record as audit_record
from ..extensions import db
from .models import Account, AccountingVoucher, Branch, FiscalPeriod, JournalEntry, JournalLine


def _check_open_period(entry_date):
    period = FiscalPeriod.query.filter(
        FiscalPeriod.starts_on <= entry_date,
        FiscalPeriod.ends_on >= entry_date,
    ).first()
    if not period:
        raise ValueError("لا توجد فترة مالية لهذا التاريخ")
    if period.status != "open":
        raise ValueError("الفترة المالية مغلقة")
    return period


def next_account_code(parent_id=None):
    query = Account.query
    if parent_id:
        parent = db.session.get(Account, parent_id)
        if not parent or not parent.is_active:
            raise ValueError("الحساب الأب غير موجود")
        prefix = parent.code
        siblings = query.filter(Account.parent_id == parent_id).all()
        nums = []
        for sibling in siblings:
            suffix = sibling.code[len(prefix):]
            if suffix.isdigit():
                nums.append(int(suffix))
        next_suffix = ((max(nums) if nums else 0) + 1)
        return f"{prefix}{next_suffix:02d}"
    roots = query.filter(Account.parent_id.is_(None)).all()
    nums = []
    for root in roots:
        try:
            nums.append(int(root.code))
        except ValueError:
            pass
    return str((max(nums) if nums else 1000) + 1000)


def get_postable_accounts(branch_id=None):
    query = Account.query.filter_by(is_active=True, is_control=False).order_by(Account.code)
    accounts = query.all()
    return [a for a in accounts if not a.children]


def _require_postable_account(account_id):
    account = db.session.get(Account, int(account_id))
    if not account or not account.is_postable:
        raise ValueError("الحساب المختار يجب أن يكون حسابًا فرعيًا تفصيليًا ولا يملك حسابات فرعية")
    return account


def get_default_branch():
    branch = Branch.query.filter_by(is_active=True).order_by(Branch.id).first()
    if not branch:
        raise ValueError("لا يوجد فرع محاسبي نشط")
    return branch


def create_account(name_ar, account_type, parent_id=None, code=None):
    name_ar = (name_ar or "").strip()
    if not name_ar:
        raise ValueError("اسم الحساب مطلوب")
    if account_type not in {"asset", "liability", "equity", "revenue", "expense"}:
        raise ValueError("نوع الحساب غير صحيح")
    code = (code or next_account_code(parent_id)).strip()
    if Account.query.filter_by(code=code).first():
        raise ValueError("رمز الحساب مستخدم")
    account = Account(code=code, name_ar=name_ar, account_type=account_type, parent_id=parent_id, is_control=False)
    db.session.add(account)
    if parent_id:
        parent = db.session.get(Account, parent_id)
        if parent:
            parent.is_control = True
    db.session.flush()
    audit_record("account.create", "Account", account.id, after={"code": account.code, "name_ar": account.name_ar})
    return account


def post_entry(number, description_ar, lines, entry_date=None, reference_type=None, reference_id=None, user_id=None, branch_id=None):
    entry_date = entry_date or date.today()
    _check_open_period(entry_date)
    if JournalEntry.query.filter_by(number=number).first():
        raise ValueError("رقم القيد مستخدم")

    branch = db.session.get(Branch, int(branch_id)) if branch_id else get_default_branch()
    if not branch or not branch.is_active:
        raise ValueError("الفرع المحاسبي غير موجود أو غير نشط")

    entry = JournalEntry(
        number=number,
        entry_date=entry_date,
        description_ar=(description_ar or "").strip(),
        reference_type=reference_type,
        reference_id=reference_id,
        status="posted",
        created_by_id=user_id,
        branch_id=branch.id,
        posted_at=datetime.now(timezone.utc),
    )
    if not entry.description_ar:
        raise ValueError("وصف القيد مطلوب")

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    if len(lines) < 2:
        raise ValueError("القيد يحتاج إلى سطرين على الأقل")

    for item in lines:
        account = _require_postable_account(item["account_id"])
        debit = Decimal(str(item.get("debit", 0)))
        credit = Decimal(str(item.get("credit", 0)))
        if not JournalLine.amount_is_valid(debit, credit):
            raise ValueError("كل سطر محاسبي يجب أن يحتوي مدينًا أو دائنًا فقط")
        total_debit += debit
        total_credit += credit
        entry.lines.append(JournalLine(
            account_id=item["account_id"],
            cost_center_id=item.get("cost_center_id"),
            party_type=item.get("party_type"),
            party_id=item.get("party_id"),
            description_ar=item.get("description_ar"),
            debit=debit,
            credit=credit,
        ))

    if total_debit <= 0 or total_debit != total_credit:
        raise ValueError("القيد غير متوازن")

    db.session.add(entry)
    db.session.flush()
    audit_record("journal.post", "JournalEntry", entry.id, after={"number": number, "debit": str(total_debit), "credit": str(total_credit)})
    return entry


def create_voucher(voucher_type, amount, from_account_id, to_account_id, voucher_date=None,
                   branch_id=None, reference=None, description_ar="", user_id=None):
    if voucher_type not in {"receipt", "payment", "transfer"}:
        raise ValueError("نوع السند غير صحيح")
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("مبلغ السند يجب أن يكون أكبر من صفر")

    from_account = _require_postable_account(from_account_id)
    to_account = _require_postable_account(to_account_id)
    if from_account.id == to_account.id:
        raise ValueError("لا يمكن أن يكون طرفا السند الحساب نفسه")

    branch = db.session.get(Branch, int(branch_id)) if branch_id else get_default_branch()
    if not branch or not branch.is_active:
        raise ValueError("الفرع المحاسبي غير موجود أو غير نشط")

    day = voucher_date or date.today()
    voucher = AccountingVoucher(
        voucher_no=f"{voucher_type[:3].upper()}-{uuid4().hex[:10].upper()}",
        voucher_type=voucher_type,
        voucher_date=day,
        branch_id=branch.id,
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=amount,
        reference=(reference or "").strip() or None,
        description_ar=(description_ar or "").strip(),
        created_by_id=user_id,
        status="posted",
    )
    if not voucher.description_ar:
        raise ValueError("بيان السند مطلوب")

    entry = post_entry(
        number=f"JV-VCH-{uuid4().hex[:10].upper()}",
        description_ar=voucher.description_ar,
        entry_date=day,
        lines=[
            {"account_id": from_account.id, "debit": amount, "credit": 0},
            {"account_id": to_account.id, "debit": 0, "credit": amount},
        ],
        reference_type="voucher",
        user_id=user_id,
        branch_id=branch.id,
    )
    voucher.journal_entry_id = entry.id
    db.session.add(voucher)
    audit_record("voucher.create", "AccountingVoucher", voucher.id or 0, after={
        "type": voucher.voucher_type, "amount": str(amount),
        "branch_id": branch.id, "from_account_id": from_account.id, "to_account_id": to_account.id,
    })
    db.session.flush()
    return voucher
