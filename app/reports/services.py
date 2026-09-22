from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func
from ..accounting.models import Account, JournalEntry, JournalLine
from ..extensions import db
from ..invoices.models import Invoice
from ..models import Booking, BookingAllocation, Customer, Resource
from ..payments.models import Payment

def date_bounds(start_date=None, end_date=None):
    start_date = start_date or date.today()
    end_date = end_date or start_date
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return start, end

def dashboard_snapshot():
    return {
        "bookings": Booking.query.count(),
        "confirmed": Booking.query.filter_by(status="confirmed").count(),
        "customers": Customer.query.filter_by(is_active=True).count(),
        "resources": Resource.query.filter_by(is_active=True).count(),
        "payments_total": str(db.session.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.status=="completed").scalar() or 0),
        "invoice_balance": str(db.session.query(func.coalesce(func.sum(Invoice.balance_due),0)).scalar() or 0),
    }

def financial_summary(start_date=None, end_date=None):
    start, end = date_bounds(start_date, end_date)
    revenue_ids = [a.id for a in Account.query.filter_by(account_type="revenue", is_active=True).all()]
    expense_ids = [a.id for a in Account.query.filter_by(account_type="expense", is_active=True).all()]
    revenue = db.session.query(func.coalesce(func.sum(JournalLine.credit-JournalLine.debit),0)).join(JournalEntry,JournalLine.entry_id==JournalEntry.id).filter(JournalLine.account_id.in_(revenue_ids or [-1]),JournalEntry.entry_date>=start.date(),JournalEntry.entry_date<end.date(),JournalEntry.status=="posted").scalar() or 0
    expenses = db.session.query(func.coalesce(func.sum(JournalLine.debit-JournalLine.credit),0)).join(JournalEntry,JournalLine.entry_id==JournalEntry.id).filter(JournalLine.account_id.in_(expense_ids or [-1]),JournalEntry.entry_date>=start.date(),JournalEntry.entry_date<end.date(),JournalEntry.status=="posted").scalar() or 0
    paid = db.session.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.status=="completed",Payment.paid_at>=start,Payment.paid_at<end).scalar() or 0
    return {"revenue":str(revenue),"expenses":str(expenses),"net":str(revenue-expenses),"cash_collected":str(paid),"invoices_issued":Invoice.query.filter(Invoice.issue_date>=start.date(),Invoice.issue_date<end.date()).count()}

def trial_balance():
    result=[]
    for account in Account.query.filter_by(is_active=True).order_by(Account.code):
        debit,credit=db.session.query(func.coalesce(func.sum(JournalLine.debit),0),func.coalesce(func.sum(JournalLine.credit),0)).join(JournalEntry,JournalLine.entry_id==JournalEntry.id).filter(JournalLine.account_id==account.id,JournalEntry.status=="posted").first()
        result.append({"code":account.code,"name_ar":account.name_ar,"type":account.account_type,"debit":str(debit or 0),"credit":str(credit or 0),"balance":str((debit or 0)-(credit or 0))})
    return result

def booking_report(start_date=None,end_date=None):
    start,end=date_bounds(start_date,end_date)
    rows=Booking.query.filter(Booking.start_at<end,Booking.end_at>=start).all()
    by_status={}
    for row in rows: by_status[row.status]=by_status.get(row.status,0)+1
    return {"total":len(rows),"by_status":by_status,"revenue":str(sum((row.total or 0) for row in rows))}

def utilization_report(start_date=None,end_date=None):
    start,end=date_bounds(start_date,end_date)
    result=[]
    for resource in Resource.query.filter_by(is_active=True).order_by(Resource.id).all():
        allocations=BookingAllocation.query.join(Booking).filter(BookingAllocation.resource_id==resource.id,BookingAllocation.is_active.is_(True),Booking.start_at<end,Booking.end_at>start,Booking.status.in_(["confirmed","checked_in","in_progress","completed"])).all()
        hours=sum((a.end_at-a.start_at).total_seconds()/3600 for a in allocations)
        result.append({"resource":resource.name_ar,"booked_hours":round(hours,2),"bookings":len(allocations)})
    return result

def ledger(account_id, start_date=None, end_date=None):
    from sqlalchemy import and_
    start, end = date_bounds(start_date, end_date)
    account = db.session.get(Account, int(account_id))
    if not account:
        raise ValueError("الحساب غير موجود")
    rows = JournalLine.query.join(JournalEntry).filter(
        JournalLine.account_id == account.id,
        JournalEntry.status == "posted",
        JournalEntry.entry_date >= start.date(),
        JournalEntry.entry_date < end.date(),
    ).order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id).all()
    running = 0
    result = []
    for row in rows:
        running += float(row.debit or 0) - float(row.credit or 0)
        result.append({
            "entry_no": row.entry.number,
            "date": row.entry.entry_date,
            "description": row.entry.description_ar,
            "debit": str(row.debit or 0),
            "credit": str(row.credit or 0),
            "balance": str(running),
        })
    return {"account": account, "rows": result, "opening": "0", "closing": str(running)}


def income_statement(start_date=None, end_date=None):
    start, end = date_bounds(start_date, end_date)
    rows = []
    for account_type, label in (("revenue", "الإيرادات"), ("expense", "المصروفات")):
        accounts = Account.query.filter_by(account_type=account_type, is_active=True).order_by(Account.code).all()
        section = []
        total = 0
        for account in accounts:
            debit, credit = db.session.query(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            ).join(JournalEntry).filter(
                JournalLine.account_id == account.id,
                JournalEntry.status == "posted",
                JournalEntry.entry_date >= start.date(),
                JournalEntry.entry_date < end.date(),
            ).first()
            value = float((credit or 0) - (debit or 0)) if account_type == "revenue" else float((debit or 0) - (credit or 0))
            total += value
            section.append({"code": account.code, "name_ar": account.name_ar, "value": value})
        rows.append({"label": label, "items": section, "total": total})
    revenue_total = rows[0]["total"] if rows else 0
    expense_total = rows[1]["total"] if len(rows) > 1 else 0
    return {"sections": rows, "net": revenue_total - expense_total}


def balance_sheet(end_date=None):
    as_of = end_date or date.today()
    sections = {}
    for account_type, label in (("asset", "الأصول"), ("liability", "الالتزامات"), ("equity", "حقوق الملكية")):
        accounts = Account.query.filter_by(account_type=account_type, is_active=True).order_by(Account.code).all()
        items = []
        total = 0
        for account in accounts:
            debit, credit = db.session.query(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            ).join(JournalEntry).filter(
                JournalLine.account_id == account.id,
                JournalEntry.status == "posted",
                JournalEntry.entry_date <= as_of,
            ).first()
            value = float((debit or 0) - (credit or 0))
            if account_type in {"liability", "equity"}:
                value = -value
            items.append({"code": account.code, "name_ar": account.name_ar, "value": value})
            total += value
        sections[label] = {"items": items, "total": total}
    return sections
