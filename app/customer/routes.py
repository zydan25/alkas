from flask import Blueprint, render_template, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..bookings.models import Booking, BookingAllocation, BookingMessage, BookingPaymentReceipt
from ..customers.models import Customer
from ..invoices.models import Invoice
from ..notifications.models import Notification
from ..policies.models import BookingPolicy, PaymentPolicy
from ..settings.services import get_site_settings

bp = Blueprint("customer", __name__, url_prefix="/customer", template_folder="templates")


def _customer():
    return Customer.query.filter_by(user_id=current_user.id, is_active=True).first()


def _owned_booking(booking_id):
    customer = _customer()
    if not customer:
        return None, customer
    booking = (
        Booking.query
        .options(
            joinedload(Booking.allocations).joinedload(BookingAllocation.resource),
            joinedload(Booking.customer),
        )
        .filter_by(id=booking_id, customer_id=customer.id)
        .first()
    )
    return booking, customer


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
    rows = (
        Booking.query
        .options(joinedload(Booking.allocations).joinedload(BookingAllocation.resource))
        .filter_by(customer_id=customer.id)
        .order_by(Booking.start_at.desc())
        .limit(100).all()
    )
    return render_template("customer/bookings.html", customer=customer, bookings=rows)


@bp.get("/bookings/<int:booking_id>")
@login_required
def booking_detail(booking_id):
    booking, customer = _owned_booking(booking_id)
    if not booking:
        return render_template("customer/no_profile.html") if not customer else (jsonify({"error":"الحجز غير موجود أو لا تملك الوصول إليه"}),404)

    invoice = Invoice.query.filter_by(booking_id=booking.id).order_by(Invoice.id.desc()).first()
    messages = BookingMessage.query.filter_by(booking_id=booking.id).order_by(BookingMessage.created_at.asc()).all()
    receipts = BookingPaymentReceipt.query.filter_by(booking_id=booking.id).order_by(BookingPaymentReceipt.created_at.desc()).all()
    return render_template(
        "customer/booking_detail.html",
        customer=customer,
        booking=booking,
        invoice=invoice,
        messages=messages,
        receipts=receipts,
        payment_policy=PaymentPolicy.query.filter_by(is_default=True, is_active=True).first(),
        booking_policy=BookingPolicy.query.filter_by(is_default=True, is_active=True).first(),
        site_settings=get_site_settings(),
    )


@bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    return render_template("customer/notifications.html", notifications=rows)


@bp.get("/profile")
@login_required
def profile():
    customer = _customer()
    is_admin = current_user.username == "admin" or current_user.has_permission("booking.view")
    # Staff/admin users may not have a Customer row; their account page must still open.
    return render_template(
        "customer/profile.html",
        customer=customer,
        is_admin=is_admin,
    )
