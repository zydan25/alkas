from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import or_

from ..invoices.models import Invoice
from ..models import Booking, Customer

bp = Blueprint("admin_search", __name__, url_prefix="/admin/search")

@bp.get("")
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"customers": [], "bookings": [], "invoices": []})

    like = f"%{q}%"
    customers = Customer.query.filter(
        Customer.is_active.is_(True),
        or_(Customer.name.ilike(like), Customer.phone.ilike(like), Customer.customer_code.ilike(like)),
    ).order_by(Customer.id.desc()).limit(8).all()

    bookings = Booking.query.filter(
        or_(Booking.booking_number.ilike(like), Booking.source.ilike(like))
    ).order_by(Booking.id.desc()).limit(8).all()

    invoices = Invoice.query.filter(Invoice.number.ilike(like)).order_by(Invoice.id.desc()).limit(8).all()

    return jsonify({
        "customers": [{"id": x.id, "label": x.name, "meta": x.phone or x.customer_code, "url": "/admin/customers?q=" + (x.phone or x.name)} for x in customers],
        "bookings": [{"id": x.id, "label": x.booking_number, "meta": x.status + " · " + x.payment_status, "url": "/admin/bookings"} for x in bookings],
        "invoices": [{"id": x.id, "label": x.number, "meta": "متبقي " + str(x.balance_due), "url": "/admin/invoices"} for x in invoices],
    })
