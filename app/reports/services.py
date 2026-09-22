from sqlalchemy import func
from ..models import Booking, Customer, Resource
from ..invoices.models import Invoice
from ..payments.models import Payment

def dashboard_snapshot():
    return {
        "bookings": Booking.query.count(),
        "customers": Customer.query.filter_by(is_active=True).count(),
        "resources": Resource.query.filter_by(is_active=True).count(),
        "confirmed_bookings": Booking.query.filter_by(status="confirmed").count(),
        "revenue_invoices": Invoice.query.filter(Invoice.status.in_(["paid","partially_paid"])).with_entities(func.coalesce(func.sum(Invoice.paid_amount), 0)).scalar() or 0,
        "payments": Payment.query.filter_by(status="completed").with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0,
    }
