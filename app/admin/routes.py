from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Booking, Customer, Resource
from ..employees.models import Employee
from ..invoices.models import Invoice
from ..payments.models import Payment
from ..maintenance.models import MaintenanceRequest
from ..tournaments.models import Tournament

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("")
@login_required
def dashboard():
    if not (current_user.has_permission("booking.view") or current_user.username == "admin"):
        return jsonify({"error": "forbidden"}), 403

    stats = {
        "bookings": Booking.query.count(),
        "confirmed": Booking.query.filter_by(status="confirmed").count(),
        "customers": Customer.query.filter_by(is_active=True).count(),
        "resources": Resource.query.filter_by(is_active=True).count(),
        "employees": Employee.query.filter_by(employment_status="active").count(),
        "open_maintenance": MaintenanceRequest.query.filter(MaintenanceRequest.status.in_(["open","in_progress"])).count(),
        "active_tournaments": Tournament.query.filter(Tournament.status.in_(["published","live"])).count(),
        "paid": db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status=="completed").scalar() or 0,
        "invoice_balance": db.session.query(func.coalesce(func.sum(Invoice.balance_due), 0)).scalar() or 0,
    }
    return render_template("admin/dashboard.html", stats=stats)
