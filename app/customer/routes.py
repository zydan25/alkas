from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..bookings.models import Booking, BookingAllocation, BookingMessage, BookingPaymentReceipt
from ..customers.models import Customer
from ..extensions import db
from ..invoices.models import Invoice
from ..memberships.models import Membership, MembershipMessage, MembershipRequest
from ..notifications.models import Notification, NotificationPreference
from ..policies.models import BookingPolicy, PaymentPolicy
from ..settings.services import get_site_settings
from ..users.models import User

bp = Blueprint("customer", __name__, url_prefix="/customer", template_folder="templates")

def _customer():
    return Customer.query.filter_by(user_id=current_user.id, is_active=True).first()

def _is_admin():
    return current_user.username == "admin" or current_user.has_permission("booking.view")

def _owned_booking(booking_id):
    customer = _customer()
    if not customer:
        return None, customer
    booking = (
        Booking.query
        .options(joinedload(Booking.allocations).joinedload(BookingAllocation.resource), joinedload(Booking.customer))
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
    bookings = Booking.query.options(joinedload(Booking.allocations).joinedload(BookingAllocation.resource)).filter_by(customer_id=customer.id).order_by(Booking.start_at.desc()).limit(8).all()
    invoices = Invoice.query.filter_by(customer_id=customer.id).order_by(Invoice.id.desc()).limit(6).all()
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    memberships = Membership.query.filter_by(customer_id=customer.id).order_by(Membership.id.desc()).limit(8).all()
    membership_requests = MembershipRequest.query.filter_by(customer_id=customer.id).order_by(MembershipRequest.id.desc()).limit(8).all()
    return render_template("customer/dashboard.html", customer=customer, bookings=bookings, invoices=invoices, unread=unread, memberships=memberships, membership_requests=membership_requests)

@bp.get("/bookings")
@login_required
def bookings():
    customer = _customer()
    if not customer:
        return render_template("customer/no_profile.html")
    rows = Booking.query.options(joinedload(Booking.allocations).joinedload(BookingAllocation.resource)).filter_by(customer_id=customer.id).order_by(Booking.start_at.desc()).limit(100).all()
    return render_template("customer/bookings.html", customer=customer, bookings=rows)

@bp.get("/bookings/<int:booking_id>")
@login_required
def booking_detail(booking_id):
    booking, customer = _owned_booking(booking_id)
    if not booking:
        return render_template("customer/no_profile.html") if not customer else (jsonify({"error": "الحجز غير موجود أو لا تملك الوصول إليه"}), 404)
    invoice = Invoice.query.filter_by(booking_id=booking.id).order_by(Invoice.id.desc()).first()
    messages = BookingMessage.query.filter_by(booking_id=booking.id).order_by(BookingMessage.created_at.asc()).all()
    receipts = BookingPaymentReceipt.query.filter_by(booking_id=booking.id).order_by(BookingPaymentReceipt.created_at.desc()).all()
    return render_template("customer/booking_detail.html", customer=customer, booking=booking, invoice=invoice, messages=messages, receipts=receipts, payment_policy=PaymentPolicy.query.filter_by(is_default=True, is_active=True).first(), booking_policy=BookingPolicy.query.filter_by(is_default=True, is_active=True).first(), site_settings=get_site_settings())

@bp.get("/notifications")
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).limit(100).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return render_template("customer/notifications.html", notifications=rows)

@bp.get("/memberships")
@login_required
def memberships():
    customer = _customer()
    if not customer:
        return redirect(url_for("customer.profile"))
    rows = MembershipRequest.query.filter_by(customer_id=customer.id).order_by(MembershipRequest.id.desc()).limit(100).all()
    active = Membership.query.filter_by(customer_id=customer.id).order_by(Membership.id.desc()).limit(100).all()
    return render_template("customer/memberships.html", customer=customer, requests=rows, memberships=active)

@bp.get("/memberships/<int:request_id>")
@login_required
def membership_detail(request_id):
    customer = _customer()
    if not customer:
        return redirect(url_for("customer.profile"))
    row = MembershipRequest.query.filter_by(id=request_id, customer_id=customer.id).first_or_404()
    messages = row.messages.order_by(MembershipMessage.created_at.asc()).all()
    active_membership = Membership.query.filter_by(customer_id=customer.id, plan_id=row.plan_id, status="active").order_by(Membership.id.desc()).first()
    return render_template("customer/membership_detail.html", customer=customer, row=row, messages=messages, active_membership=active_membership)

@bp.post("/memberships/<int:request_id>/cancel")
@login_required
def membership_cancel(request_id):
    customer = _customer()
    if not customer:
        return jsonify({"error": "ملف العميل غير موجود"}), 403
    row = MembershipRequest.query.filter_by(id=request_id, customer_id=customer.id).first_or_404()
    if row.status not in {"pending", "approved"}:
        return jsonify({"error": "لا يمكن إلغاء هذا الطلب في حالته الحالية"}), 400
    payload = request.get_json(silent=True) or {}
    reason = (request.form.get("reason_ar") or payload.get("reason_ar") or "").strip()
    if len(reason) < 2:
        return jsonify({"error": "اكتب سبب الإلغاء"}), 400
    row.status = "cancelled"
    row.cancellation_reason = reason
    active = Membership.query.filter_by(customer_id=customer.id, plan_id=row.plan_id, status="active").order_by(Membership.id.desc()).first()
    if active:
        active.status = "cancelled"
    db.session.add(Notification(user_id=current_user.id, title_ar="تم إلغاء طلب العضوية", body_ar=f"{row.title_ar}: {reason}", kind="membership", priority="normal"))
    db.session.commit()
    return redirect(url_for("customer.memberships"))

@bp.post("/memberships/<int:request_id>/messages")
@login_required
def membership_message(request_id):
    customer = _customer()
    if not customer:
        return jsonify({"error": "غير مصرح"}), 403
    row = MembershipRequest.query.filter_by(id=request_id, customer_id=customer.id).first_or_404()
    body = (request.form.get("body_ar") or (request.get_json(silent=True) or {}).get("body_ar") or "").strip()
    if not body:
        return jsonify({"error": "اكتب رسالتك"}), 400
    db.session.add(MembershipMessage(request_id=row.id, sender_user_id=current_user.id, sender_role="customer", body_ar=body))
    db.session.commit()
    return redirect(url_for("customer.membership_detail", request_id=row.id))

@bp.post("/profile/update")
@login_required
def update_profile():
    customer = _customer()
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    email = (request.form.get("email") or "").strip() or None
    if len(name) < 2:
        return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), error="الاسم مطلوب بشكل صحيح"), 400
    if phone:
        conflict = Customer.query.filter(Customer.phone == phone, Customer.id != (customer.id if customer else -1)).first()
        user_conflict = User.query.filter(User.phone == phone, User.id != current_user.id).first()
        if conflict or user_conflict:
            return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), error="رقم الهاتف مستخدم في حساب آخر"), 400
    current_user.display_name = name
    current_user.phone = phone or None
    if customer:
        customer.name = name
        customer.phone = phone or None
        customer.email = email
    db.session.commit()
    return redirect(url_for("customer.profile"))

@bp.post("/profile/password")
@login_required
def update_password():
    customer = _customer()
    old = request.form.get("current_password") or ""
    new = request.form.get("new_password") or ""
    confirm = request.form.get("confirm_password") or ""
    if not current_user.check_password(old):
        return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), password_error="كلمة المرور الحالية غير صحيحة"), 400
    if len(new) < 8:
        return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), password_error="كلمة المرور الجديدة يجب أن تكون 8 أحرف أو أكثر"), 400
    if new != confirm:
        return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), password_error="تأكيد كلمة المرور غير مطابق"), 400
    current_user.set_password(new)
    db.session.add(Notification(user_id=current_user.id, title_ar="تم تحديث كلمة المرور", body_ar="تم تغيير كلمة مرور حسابك بنجاح.", kind="security", priority="high"))
    db.session.commit()
    return redirect(url_for("customer.profile"))

@bp.get("/profile")
@login_required
def profile():
    customer = _customer()
    memberships = Membership.query.filter_by(customer_id=customer.id).order_by(Membership.id.desc()).limit(6).all() if customer else []
    membership_requests = MembershipRequest.query.filter_by(customer_id=customer.id).order_by(MembershipRequest.id.desc()).limit(6).all() if customer else []
    recent_bookings = Booking.query.filter_by(customer_id=customer.id).order_by(Booking.start_at.desc()).limit(6).all() if customer else []
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    return render_template("customer/profile.html", customer=customer, is_admin=_is_admin(), memberships=memberships, membership_requests=membership_requests, recent_bookings=recent_bookings, unread=unread, preferences=prefs)
