from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..accounting.models import Account, JournalEntry
from ..employees.models import Employee
from ..extensions import db
from ..invoices.models import Invoice
from ..maintenance.models import MaintenanceRequest
from ..models import Booking, BookingAllocation, Customer, Resource
from ..payments.models import Payment
from ..tournaments.models import Tournament

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _allowed():
    return current_user.has_permission("booking.view") or current_user.username == "admin"


STATUS_LABELS = {
    "hold": "مؤقت", "pending": "قيد المراجعة", "confirmed": "مؤكد",
    "checked_in": "حضر", "in_progress": "جاري", "completed": "مكتمل",
    "cancelled": "ملغى", "no_show": "لم يحضر", "expired": "منتهي",
}


def _booking_tone(status):
    return {
        "confirmed": "success", "checked_in": "success", "in_progress": "info",
        "hold": "warning", "pending": "warning", "cancelled": "danger",
        "no_show": "danger", "expired": "muted", "completed": "neutral",
    }.get(status, "neutral")


@bp.get("")
@login_required
def dashboard():
    if not _allowed():
        return {"error": "forbidden"}, 403

    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    bookings = (
        Booking.query
        .options(joinedload(Booking.customer), joinedload(Booking.allocations).joinedload(BookingAllocation.resource))
        .filter(Booking.start_at < end, Booking.end_at > start)
        .order_by(Booking.start_at)
        .limit(80).all()
    )

    today_bookings = []
    for b in bookings:
        tone = _booking_tone(b.status)
        today_bookings.append({
            "id": b.id,
            "start_at": b.start_at,
            "end_at": b.end_at,
            "customer_name": b.customer.name if b.customer else "بدون عميل",
            "resource_names": [a.resource.name_ar for a in b.allocations if a.resource],
            "status_ar": STATUS_LABELS.get(b.status, b.status),
            "tone": tone,
        })

    resources_status = []
    for resource in Resource.query.filter_by(is_active=True).order_by(Resource.id).limit(24):
        status_map = {
            "available": ("متاح", "success"),
            "maintenance": ("صيانة", "warning"),
            "closed": ("مغلق", "danger"),
            "private": ("خاص", "info"),
            "event_only": ("فعاليات", "info"),
            "temporarily_blocked": ("محجوب", "warning"),
        }
        label, tone = status_map.get(resource.status, (resource.status, "neutral"))
        resources_status.append({"name": resource.name_ar, "status": label, "tone": tone})

    weekly = []
    max_count = 1
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        s = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        e = s + timedelta(days=1)
        count = Booking.query.filter(Booking.start_at < e, Booking.end_at > s).count()
        max_count = max(max_count, count)
        weekly.append({"label": d.strftime("%a"), "count": count})
    for item in weekly:
        item["height"] = max(8, int(item["count"] / max_count * 100))

    stats = {
        "bookings": Booking.query.count(),
        "confirmed": Booking.query.filter_by(status="confirmed").count(),
        "customers": Customer.query.filter_by(is_active=True).count(),
        "resources": Resource.query.filter_by(is_active=True).count(),
        "employees": Employee.query.filter_by(employment_status="active").count(),
        "open_maintenance": MaintenanceRequest.query.filter(MaintenanceRequest.status.in_(["open", "in_progress"])).count(),
        "active_tournaments": Tournament.query.filter(Tournament.status.in_(["published", "live"])).count(),
        "paid": db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == "completed").scalar() or 0,
        "invoice_balance": db.session.query(func.coalesce(func.sum(Invoice.balance_due), 0)).scalar() or 0,
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        today_bookings=today_bookings,
        resources_status=resources_status,
        weekly_bookings=weekly,
    )


@bp.get("/bookings")
@login_required
def bookings():
    if not _allowed():
        return {"error": "forbidden"}, 403

    selected = request.args.get("date")
    try:
        selected_date = datetime.strptime(selected, "%Y-%m-%d").date() if selected else date.today()
    except ValueError:
        selected_date = date.today()

    start = datetime(selected_date.year, selected_date.month, selected_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    rows = (
        Booking.query
        .options(joinedload(Booking.customer), joinedload(Booking.allocations).joinedload(BookingAllocation.resource))
        .filter(Booking.start_at < end, Booking.end_at > start)
        .order_by(Booking.start_at, Booking.id)
        .all()
    )

    timeline = [{
        "id": b.id,
        "number": b.booking_number,
        "customer": b.customer.name if b.customer else "بدون عميل",
        "phone": b.customer.phone if b.customer else "",
        "start": b.start_at,
        "end": b.end_at,
        "resources": [a.resource.name_ar for a in b.allocations if a.resource],
        "status": STATUS_LABELS.get(b.status, b.status),
        "tone": _booking_tone(b.status),
        "payment_status": b.payment_status,
        "total": b.total,
    } for b in rows]

    return render_template(
        "admin/bookings.html",
        selected_date=selected_date,
        timeline=timeline,
        total=len(timeline),
    )


@bp.get("/customers")
@login_required
def customers():
    if not _allowed():
        return {"error": "forbidden"}, 403
    q = (request.args.get("q") or "").strip()
    query = Customer.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter((Customer.name.ilike(like)) | (Customer.phone.ilike(like)) | (Customer.customer_code.ilike(like)))
    rows = query.order_by(Customer.id.desc()).limit(100).all()
    return render_template("admin/customers.html", rows=rows, q=q)


@bp.get("/resources")
@login_required
def resources():
    if not _allowed():
        return {"error": "forbidden"}, 403
    rows = Resource.query.options(joinedload(Resource.sport), joinedload(Resource.zone)).filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all()
    return render_template("admin/resources.html", rows=rows)


@bp.get("/money")
@login_required
def money():
    if not current_user.has_permission("accounting.view") and current_user.username != "admin":
        return {"error": "forbidden"}, 403
    account_count = Account.query.filter_by(is_active=True).count()
    entries = JournalEntry.query.order_by(JournalEntry.id.desc()).limit(20).all()
    invoices = Invoice.query.order_by(Invoice.id.desc()).limit(12).all()
    payments = Payment.query.order_by(Payment.id.desc()).limit(12).all()
    return render_template("admin/money.html", account_count=account_count, entries=entries, invoices=invoices, payments=payments)
