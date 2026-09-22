from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..invoices.models import Invoice
from ..models import Booking, Customer, Resource
from ..payments.models import Payment
from .models import SavedReport

bp = Blueprint("reports", __name__, url_prefix="/admin/reports")


@bp.get("")
@login_required
def ui():
    stats = dashboard_snapshot()
    return render_template("reports/index.html", stats=stats, saved=SavedReport.query.filter_by(owner_id=current_user.id).order_by(SavedReport.id.desc()).limit(20).all())


@bp.get("/dashboard")
@login_required
def dashboard():
    return jsonify(dashboard_snapshot())


@bp.get("/api")
@login_required
def api():
    return jsonify(dashboard_snapshot())


def dashboard_snapshot():
    return {
        "bookings": Booking.query.count(),
        "confirmed": Booking.query.filter_by(status="confirmed").count(),
        "customers": Customer.query.filter_by(is_active=True).count(),
        "resources": Resource.query.filter_by(is_active=True).count(),
        "payments_total": str(db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == "completed").scalar() or 0),
        "invoice_balance": str(db.session.query(func.coalesce(func.sum(Invoice.balance_due), 0)).scalar() or 0),
    }
