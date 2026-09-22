from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func

from ..audit.services import record as audit_record
from ..extensions import db
from .models import Account, FiscalPeriod, JournalEntry, JournalLine


def _check_open_period(entry_date):
    period = FiscalPeriod.query.filter(
        FiscalPeriod.starts_on <= entry_date,
        FiscalPeriod.ends_on >= entry_date,
    ).first()
    if period and period.status != "open":
        raise ValueError("الفترة المالية مغلقة")
    return period


def next_account_code(parent_id=None):
    query = Account.query
    if parent_id:
        parent = db.session.get(Account, parent_id)
        if not parent:
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


def create_account(name_ar, account_type, parent_id=None, code=None):
    name_ar = (name_ar or "").strip()
    if not name_ar:
        raise ValueError("اسم الحساب مطلوب")
    if account_type not in {"asset", "liability", "equity", "revenue", "expense"}:
        raise ValueError("نوع الحساب غير صحيح")
    code = (code or next_account_code(parent_id)).strip()
    if Account.query.filter_by(code=code).first():
        raise ValueError("رمز الحساب مستخدم")
    account = Account(code=code, name_ar=name_ar, account_type=account_type, parent_id=parent_id)
    db.session.add(account)
    db.session.flush()
    audit_record("account.create", "Account", account.id, after={"code": account.code, "name_ar": account.name_ar})
    return account


def post_entry(number, description_ar, lines, entry_date=None, reference_type=None, reference_id=None, user_id=None):
    entry_date = entry_date or date.today()
    _check_open_period(entry_date)
    if JournalEntry.query.filter_by(number=number).first():
        raise ValueError("رقم القيد مستخدم")

    entry = JournalEntry(
        number=number,
        entry_date=entry_date,
        description_ar=(description_ar or "").strip(),
        reference_type=reference_type,
        reference_id=reference_id,
        status="posted",
        created_by_id=user_id,
        posted_at=datetime.now(timezone.utc),
    )
    if not entry.description_ar:
        raise ValueError("وصف القيد مطلوب")

    total_debit = Decimal("0")
    total_credit = Decimal("0")

    if len(lines) < 2:
        raise ValueError("القيد يحتاج إلى سطرين على الأقل")

    for item in lines:
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
