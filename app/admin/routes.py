from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..accounting.models import Account, JournalEntry
from ..employees.models import Employee
from ..extensions import db
from ..invoices.models import Invoice
from ..maintenance.models import MaintenanceRequest
from ..models import Booking, BookingAllocation, Customer, Resource, Venue
from ..bookings.services import cancel_booking, create_hold_booking
from ..payments.models import Payment
from ..tournaments.models import Tournament

bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


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
        .options(
            joinedload(Booking.customer),
            joinedload(Booking.allocations).joinedload(BookingAllocation.resource),
        )
        .filter(Booking.start_at < end, Booking.end_at > start)
        .order_by(Booking.start_at)
        .limit(80).all()
    )

    today_bookings = [{
        "id": b.id,
        "start_at": b.start_at,
        "end_at": b.end_at,
        "customer_name": b.customer.name if b.customer else "بدون عميل",
        "resource_names": [a.resource.name_ar for a in b.allocations if a.resource],
        "status_ar": STATUS_LABELS.get(b.status, b.status),
        "tone": _booking_tone(b.status),
    } for b in bookings]

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
        "id": b.id, "number": b.booking_number,
        "customer": b.customer.name if b.customer else "بدون عميل",
        "phone": b.customer.phone if b.customer else "",
        "start": b.start_at, "end": b.end_at,
        "resources": [a.resource.name_ar for a in b.allocations if a.resource],
        "status": STATUS_LABELS.get(b.status, b.status),
        "tone": _booking_tone(b.status),
        "payment_status": b.payment_status, "total": b.total,
    } for b in rows]

    return render_template("admin/bookings.html", selected_date=selected_date, timeline=timeline, total=len(timeline))


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
    venues = Venue.query.filter_by(is_active=True).order_by(Venue.id).all()
    return render_template("admin/resources.html", rows=rows, venues=venues)


@bp.get("/bookings/new")
@login_required
def booking_new():
    if not current_user.has_permission("booking.create") and current_user.username != "admin":
        return {"error": "forbidden"}, 403
    return render_template(
        "admin/booking_new.html",
        customers=Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(500).all(),
        resources=Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all(),
    )


@bp.post("/bookings/new")
@login_required
def booking_create():
    if not current_user.has_permission("booking.create") and current_user.username != "admin":
        return {"error": "forbidden"}, 403
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).limit(500).all()
    resources = Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all()
    try:
        customer_id = int(request.form["customer_id"])
        start_at = datetime.fromisoformat(request.form["start_at"])
        duration = int(request.form.get("duration") or 60)
        resource_ids = [int(v) for v in request.form.getlist("resource_ids")]
        if duration <= 0 or not resource_ids:
            raise ValueError("حدد المدة وملعبًا واحدًا على الأقل")
        booking, _token = create_hold_booking(
            customer_id=customer_id,
            resource_ids=resource_ids,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=duration),
            source="staff",
            minutes=60,
        )
        from ..bookings.services import confirm_booking
        confirm_booking(booking.id, current_user.id)
    except (KeyError, ValueError, TypeError) as exc:
        return render_template("admin/booking_new.html", customers=customers, resources=resources, error=str(exc)), 400
    except Exception:
        db.session.rollback()
        return render_template("admin/booking_new.html", customers=customers, resources=resources, error="تعذر إنشاء الحجز؛ تحقق من التعارض والبيانات"), 409
    return redirect(url_for("admin.bookings", date=start_at.date().isoformat()))


@bp.post("/bookings/bulk-cancel")
@login_required
def bookings_bulk_cancel():
    if not current_user.has_permission("booking.cancel") and current_user.username != "admin":
        return {"error": "forbidden"}, 403
    ids = []
    for value in request.form.getlist("booking_ids"):
        try:
            ids.append(int(value))
        except ValueError:
            continue
    for booking_id in dict.fromkeys(ids):
        booking = db.session.get(Booking, booking_id)
        if not booking:
            continue
        try:
            cancel_booking(booking.id, "إلغاء جماعي من الإدارة", current_user.id)
        except ValueError:
            continue
    return redirect(url_for("admin.bookings"))
