from datetime import date
from decimal import Decimal

from ..extensions import db
from .models import Account, JournalEntry, JournalLine


def post_entry(number, description_ar, lines, entry_date=None, reference_type=None, reference_id=None, user_id=None):
    entry = JournalEntry(
        number=number,
        entry_date=entry_date or date.today(),
        description_ar=description_ar,
        reference_type=reference_type,
        reference_id=reference_id,
        status="posted",
        created_by_id=user_id,
    )
    total_debit = Decimal("0")
    total_credit = Decimal("0")
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
    return entry
