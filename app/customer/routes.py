from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..models import Booking, BookingAllocation, Customer
from ..notifications.models import Notification
from ..invoices.models import Invoice

bp = Blueprint("customer", __name__, url_prefix="/customer", template_folder="templates")


def _customer():
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    return customer


@bp.get("")
@login_required
def dashboard():
    customer = _customer()
    if not customer:
        return render_template("customer/no_profile.html")

    bookings = (
        Booking.query
        .options(joinedload(Booking.allocations).joinedload(BookingAllocation.resource))
        .filter_by(customer_id=customer.id)
        .order_by(Booking.start_at.desc())
        .limit(8).all()
    )
    invoices = Invoice.query.filter_by(customer_id=customer.id).order_by(Invoice.id.desc()).limit(6).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template("customer/dashboard.html", customer=customer, bookings=bookings, invoices=invoices, unread=unread)


@bp.get("/bookings")
@login_required
def bookings():
    customer = _customer()
    if not customer:
        return render_template("customer/no_profile.html")
    rows = Booking.query.filter_by(customer_id=customer.id).order_by(Booking.start_at.desc()).limit(100).all()
    return render_template("customer/bookings.html", customer=customer, bookings=rows)


@bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    return render_template("customer/notifications.html", notifications=rows)


@bp.get("/profile")
@login_required
def profile():
    customer = _customer()
    if not customer:
        return render_template("customer/no_profile.html")
    return render_template("customer/profile.html", customer=customer)
