from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from ..accounting.models import Account
from ..bookings.services import cancel_booking, confirm_booking, create_hold_booking, expire_holds
from ..cashier.models import CashShift, CashTransaction
from ..employees.models import Attendance, Employee
from ..extensions import db
from ..invoices.models import Invoice, InvoiceLine
from ..notifications.services import notify_user
from ..payments.models import Payment
from ..payments.services import record_payment_with_accounting
from ..policies.models import BookingPolicy, PaymentPolicy, RefundRequest
from ..payroll.models import EmployeeAdvance, PayrollLine, PayrollRun
from ..models import Booking, BookingAllocation, Customer, Resource, Sport
from .models import ParkVisit, ParkVisitExit, StaffDeduction

bp = Blueprint("staff", __name__, url_prefix="/staff", template_folder="templates")

TZ = ZoneInfo("Asia/Aden")
PAYMENT_METHODS = {
    "cash": "نقدي",
    "bank_transfer": "تحويل",
    "card": "بطاقة",
    "wallet": "محفظة",
}


def _employee():
    return Employee.query.filter_by(
        user_id=current_user.id,
        employment_status="active",
    ).first()


def _require_employee():
    employee = _employee()
    if not employee:
        return None, ({"error": "هذا الحساب غير مرتبط بموظف نشط"}, 403)
    return employee, None


def _can(permission):
    if current_user.username == "admin" or current_user.has_permission(permission):
        return True
    employee = _employee()
    return bool(employee and permission in {"staff.access", "staff.park.manage", "staff.finance.view", "staff.cash.manage"})


def _now():
    return datetime.now(TZ)


def _to_decimal(value, label="المبلغ", minimum=Decimal("0")):
    try:
        amount = Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} غير صالح")
    if amount < minimum:
        raise ValueError(f"{label} يجب ألا يقل عن {minimum}")
    return amount


def _normalize_datetime(raw):
    if not raw:
        return _now() + timedelta(minutes=1)
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("وقت البداية غير صحيح") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=TZ)
    return value


def _open_shift(employee):
    return (
        CashShift.query
        .filter_by(employee_id=employee.id, status="open")
        .order_by(CashShift.id.desc())
        .first()
    )


def _shift_expected(shift):
    expected = Decimal(shift.opening_amount or 0)
    for tx in CashTransaction.query.filter_by(shift_id=shift.id).all():
        if tx.transaction_type in {"sale", "receipt", "deposit"}:
            expected += Decimal(tx.amount or 0)
        elif tx.transaction_type in {"refund", "payment", "withdraw"}:
            expected -= Decimal(tx.amount or 0)
    return expected


def _general_customer():
    customer = Customer.query.filter_by(customer_code="CUS-GENERAL").first()
    if not customer:
        customer = Customer(
            customer_code="CUS-GENERAL",
            name="فريق عام",
            phone=None,
            is_active=True,
        )
        db.session.add(customer)
        db.session.flush()
    return customer


def _resolve_customer():
    customer_id = request.form.get("customer_id")
    if customer_id:
        try:
            customer = db.session.get(Customer, int(customer_id))
        except (TypeError, ValueError):
            customer = None
        if not customer or not customer.is_active:
            raise ValueError("العميل غير موجود")
        return customer
    name = (request.form.get("customer_name") or "").strip()
    phone = (request.form.get("customer_phone") or "").strip()
    if name and phone:
        customer = Customer.query.filter_by(phone=phone, is_active=True).first()
        if customer:
            return customer
        customer = Customer(
            customer_code=f"CUS-{uuid4().hex[:10].upper()}",
            name=name,
            phone=phone,
            is_active=True,
        )
        db.session.add(customer)
        db.session.flush()
        return customer
    return _general_customer()


def _ensure_method_allowed(method, payment_policy):
    if method not in PAYMENT_METHODS:
        raise ValueError("طريقة الدفع غير صحيحة")
    mapping = {
        "cash": payment_policy.allow_cash,
        "bank_transfer": payment_policy.allow_transfer,
        "card": payment_policy.allow_card,
        "wallet": payment_policy.allow_wallet,
    }
    if not mapping.get(method, False):
        raise ValueError("طريقة الدفع غير مفعّلة في سياسة الدفع")


def _confirm_with_payment(booking, employee, payment_amount, method):
    total = Decimal(booking.total or 0)
    if total <= 0:
        raise ValueError("قيمة الحجز يجب أن تكون أكبر من صفر")

    payment_policy = PaymentPolicy.query.filter_by(is_default=True, is_active=True).first()
    if payment_policy:
        _ensure_method_allowed(method, payment_policy)

    if method == "cash" and not _open_shift(employee):
        raise ValueError("افتح وردية الصندوق أولًا قبل التحصيل النقدي")

    policy = BookingPolicy.query.filter_by(is_default=True, is_active=True).first()
    minimum = total * Decimal(str(policy.deposit_percent if policy else 100)) / Decimal("100")
    if payment_policy and payment_policy.require_full_payment:
        minimum = total
    if payment_amount < minimum:
        raise ValueError(f"الحد الأدنى للتحصيل لهذا الحجز {minimum:,.2f}")

    booking, invoice = confirm_booking(booking.id, current_user.id)
    payment = record_payment_with_accounting(
        invoice_id=invoice.id,
        amount=payment_amount,
        method=method,
        number=f"PAY-{uuid4().hex[:10].upper()}",
        user_id=current_user.id,
    )
    return booking, invoice, payment


def _staff_booking_context(employee):
    now = datetime.now(timezone.utc)
    expire_holds(now)
    pending = (
        Booking.query
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.allocations).selectinload(BookingAllocation.resource),
        )
        .filter(
            Booking.status.in_(["hold", "pending"]),
            Booking.hold_expires_at.is_not(None),
            Booking.hold_expires_at > now,
        )
        .order_by(Booking.start_at)
        .limit(30)
        .all()
    )
    active = (
        Booking.query
        .options(
            selectinload(Booking.customer),
            selectinload(Booking.allocations).selectinload(BookingAllocation.resource),
        )
        .filter(
            Booking.status.in_(["confirmed", "checked_in", "in_progress"]),
            Booking.end_at >= now - timedelta(hours=2),
        )
        .order_by(Booking.start_at)
        .limit(50)
        .all()
    )
    return pending, active


@bp.get("")
@login_required
def dashboard():
    employee, error = _require_employee()
    if error:
        return render_template("staff/no_profile.html"), 403

    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=employee.id, work_date=today).first()
    shift = _open_shift(employee)
    pending, active = _staff_booking_context(employee)

    open_visits = (
        ParkVisit.query
        .filter_by(status="open")
        .order_by(ParkVisit.started_at.desc())
        .limit(50)
        .all()
    )
    occupancy = sum(int(v.people_remaining or 0) for v in open_visits)

    latest_payroll = (
        db.session.query(PayrollLine, PayrollRun)
        .join(PayrollRun, PayrollRun.id == PayrollLine.payroll_run_id)
        .filter(PayrollLine.employee_id == employee.id)
        .order_by(PayrollRun.end_date.desc(), PayrollRun.id.desc())
        .first()
    )
    deductions = (
        db.session.query(func.coalesce(func.sum(StaffDeduction.amount), 0))
        .filter(StaffDeduction.employee_id == employee.id)
        .scalar()
        or 0
    )
    advances = (
        EmployeeAdvance.query
        .filter_by(employee_id=employee.id, status="open")
        .order_by(EmployeeAdvance.issue_date.desc())
        .limit(20)
        .all()
    )
    transactions = (
        CashTransaction.query.filter(CashTransaction.shift_id == shift.id)
        .order_by(CashTransaction.id.desc()).limit(20).all()
        if shift else []
    )

    return render_template(
        "staff/dashboard.html",
        employee=employee,
        attendance=attendance,
        shift=shift,
        shift_expected=_shift_expected(shift) if shift else Decimal("0"),
        pending=pending,
        active=active,
        open_visits=open_visits,
        park_occupancy=occupancy,
        latest_payroll=latest_payroll,
        deductions=Decimal(deductions),
        advances=advances,
        transactions=transactions,
        resources=Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all(),
        sports=Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all(),
        payment_methods=PAYMENT_METHODS,
        can_confirm=_can("staff.booking.confirm"),
        can_chat=_can("staff.booking.chat"),
        can_cancel=_can("staff.booking.cancel"),
        can_park=_can("staff.park.manage"),
        today=today,
        now=_now(),
    )


@bp.get("/search")
@login_required
def search():
    employee, error = _require_employee()
    if error:
        return error

    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"items": []})

    like = f"%{q}%"
    customers = (
        Customer.query.filter(
            Customer.is_active.is_(True),
            or_(
                Customer.name.ilike(like),
                Customer.phone.ilike(like),
                Customer.customer_code.ilike(like),
            ),
        )
        .order_by(Customer.name)
        .limit(12)
        .all()
    )
    return jsonify({
        "items": [{
            "id": c.id,
            "name": c.name,
            "phone": c.phone or "",
            "code": c.customer_code,
        } for c in customers]
    })


@bp.post("/customers/new")
@login_required
def customer_new():
    employee, error = _require_employee()
    if error:
        return error

    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    if len(name) < 2:
        return jsonify({"error": "اسم العميل مطلوب"}), 400
    if phone and Customer.query.filter_by(phone=phone, is_active=True).first():
        return jsonify({"error": "رقم الهاتف مرتبط بعميل موجود"}), 400

    customer = Customer(
        customer_code=f"CUS-{uuid4().hex[:10].upper()}",
        name=name,
        phone=phone,
        is_active=True,
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone or "",
        "code": customer.customer_code,
    }), 201


@bp.post("/bookings/quick")
@login_required
def booking_quick():
    employee, error = _require_employee()
    if error:
        return error, 403

    try:
        mode = (request.form.get("mode") or "direct").strip()
        customer = _resolve_customer()
        resource_ids = [int(value) for value in request.form.getlist("resource_ids") if value]
        if not resource_ids:
            raise ValueError("اختر ملعبًا واحدًا على الأقل")

        start_at = _normalize_datetime(request.form.get("start_at"))
        if mode == "multi":
            people = int(request.form.get("people_count") or 0)
            if people <= 0:
                raise ValueError("عدد الأشخاص يجب أن يكون أكبر من صفر")
            duration = int(request.form.get("duration") or 0)
            if duration <= 0:
                raise ValueError("حدد مدة اللعب بالدقائق")
            per_person = _to_decimal(request.form.get("price_per_person"), "سعر الشخص", Decimal("0.01"))
            base_price = (per_person * Decimal(people)).quantize(Decimal("0.01"))
            discount = _to_decimal(request.form.get("discount"), "الخصم")
            end_at = start_at + timedelta(minutes=duration)
        else:
            duration = int(request.form.get("duration") or 60)
            if duration <= 0:
                raise ValueError("المدة يجب أن تكون أكبر من صفر")
            end_at = start_at + timedelta(minutes=duration)
            base_price = _to_decimal(request.form.get("price"), "السعر", Decimal("0.01"))
            discount = _to_decimal(request.form.get("discount"), "الخصم")
            if discount > base_price:
                raise ValueError("الخصم لا يمكن أن يتجاوز السعر")

        booking, _token = create_hold_booking(
            customer_id=customer.id,
            resource_ids=resource_ids,
            start_at=start_at,
            end_at=end_at,
            source="staff",
            minutes=10,
        )

        existing = sum((Decimal(a.price or 0) for a in booking.allocations), Decimal("0"))
        if existing <= 0:
            booking.allocations[0].price = base_price
        else:
            factor = base_price / existing
            for allocation in booking.allocations:
                allocation.price = (Decimal(allocation.price or 0) * factor).quantize(Decimal("0.01"))
        booking.subtotal = base_price
        booking.discount = discount
        booking.tax = Decimal("0")
        booking.total = max(Decimal("0"), base_price - discount)
        db.session.commit()

        paid = _to_decimal(request.form.get("paid_amount") or booking.total, "المبلغ المدفوع")
        if paid > booking.total:
            paid = booking.total
        method = request.form.get("method") or "cash"
        booking, invoice, payment = _confirm_with_payment(booking, employee, paid, method)

        return jsonify({
            "ok": True,
            "booking_id": booking.id,
            "booking_number": booking.booking_number,
            "invoice_number": invoice.number,
            "paid": str(payment.amount),
            "total": str(invoice.total),
            "balance": str(invoice.balance_due),
        })
    except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "تعذر إنشاء الحجز السريع، تحقق من التعارض ووردية الصندوق"}), 409


@bp.post("/bookings/<int:booking_id>/confirm")
@login_required
def booking_confirm(booking_id):
    employee, error = _require_employee()
    if error:
        return error, 403
    if not _can("staff.booking.confirm"):
        return jsonify({"error": "لا تملك صلاحية تأكيد حجوزات العملاء"}), 403

    booking = (
        Booking.query
        .options(selectinload(Booking.customer), selectinload(Booking.allocations).selectinload(BookingAllocation.resource))
        .get_or_404(booking_id)
    )
    if booking.status not in {"hold", "pending"}:
        return jsonify({"error": "الحجز ليس قيد الانتظار"}), 400
    try:
        amount = _to_decimal(request.form.get("paid_amount"), "المبلغ المدفوع", Decimal("0.01"))
        method = request.form.get("method") or "cash"
        booking, invoice, payment = _confirm_with_payment(booking, employee, amount, method)
        return jsonify({
            "ok": True,
            "booking_id": booking.id,
            "booking_number": booking.booking_number,
            "invoice_number": invoice.number,
            "total": str(invoice.total),
            "paid": str(payment.amount),
            "balance": str(invoice.balance_due),
        })
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400


@bp.post("/bookings/<int:booking_id>/cancel")
@login_required
def booking_cancel(booking_id):
    employee, error = _require_employee()
    if error:
        return error, 403
    if not _can("staff.booking.cancel"):
        return jsonify({"error": "لا تملك صلاحية إلغاء الحجوزات"}), 403
    reason = (request.form.get("reason") or "إلغاء من لوحة الموظف").strip()
    try:
        booking, requested_refund = cancel_booking(booking_id, reason, current_user.id)
        return jsonify({
            "ok": True,
            "status": booking.status,
            "requested_refund": str(requested_refund),
        })
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400


@bp.get("/bookings/<int:booking_id>/chat")
@login_required
def booking_chat(booking_id):
    employee, error = _require_employee()
    if error:
        return render_template("staff/no_profile.html"), 403
    if not _can("staff.booking.chat"):
        return jsonify({"error": "لا تملك صلاحية فتح المحادثات"}), 403
    from ..bookings.models import BookingMessage
    booking = (
        Booking.query
        .options(selectinload(Booking.customer))
        .get_or_404(booking_id)
    )
    messages = BookingMessage.query.filter_by(booking_id=booking.id).order_by(BookingMessage.created_at.asc()).all()
    return render_template("staff/chat.html", employee=employee, booking=booking, messages=messages)


@bp.post("/bookings/<int:booking_id>/chat")
@login_required
def booking_chat_send(booking_id):
    employee, error = _require_employee()
    if error:
        return error, 403
    if not _can("staff.booking.chat"):
        return jsonify({"error": "لا تملك صلاحية فتح المحادثات"}), 403
    from ..bookings.models import BookingMessage
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({"error": "الحجز غير موجود"}), 404
    body = (request.form.get("body_ar") or "").strip()
    if not body:
        return jsonify({"error": "اكتب الرسالة"}), 400

    message = BookingMessage(
        booking_id=booking.id,
        sender_user_id=current_user.id,
        sender_role="staff",
        message_type="message",
        body_ar=body,
    )
    db.session.add(message)
    db.session.commit()
    if booking.customer and booking.customer.user_id:
        notify_user(
            booking.customer.user_id,
            "رسالة من ملاعب الكأس",
            body,
            "booking",
            "normal",
        )
    return jsonify({"ok": True, "body_ar": body, "created_at": message.created_at.isoformat()}), 201


@bp.get("/park")
@login_required
def park():
    employee, error = _require_employee()
    if error:
        return render_template("staff/no_profile.html"), 403
    if not _can("staff.park.manage"):
        return jsonify({"error": "لا تملك صلاحية إدارة دخول الحديقة"}), 403
    visits = ParkVisit.query.filter_by(status="open").order_by(ParkVisit.started_at.desc()).limit(100).all()
    return render_template("staff/park.html", employee=employee, visits=visits, occupancy=sum(v.people_remaining for v in visits))


@bp.post("/park/entry")
@login_required
def park_entry():
    employee, error = _require_employee()
    if error:
        return error, 403
    if not _can("staff.park.manage"):
        return jsonify({"error": "لا تملك صلاحية إدارة دخول الحديقة"}), 403

    try:
        customer = _resolve_customer()
        visitor_name = (request.form.get("visitor_name") or customer.name or "زائر").strip()
        people = int(request.form.get("people_count") or 0)
        if people <= 0:
            raise ValueError("عدد الأشخاص يجب أن يكون أكبر من صفر")
        price_per_person = _to_decimal(request.form.get("price_per_person"), "سعر الشخص", Decimal("0.01"))
        total = (price_per_person * Decimal(people)).quantize(Decimal("0.01"))
        end_raw = (request.form.get("expected_end_at") or "").strip()
        expected_end_at = None
        if end_raw:
            expected_end_at = _normalize_datetime(end_raw)
            if expected_end_at <= _now():
                raise ValueError("وقت الخروج المتوقع يجب أن يكون في المستقبل")

        method = request.form.get("method") or "cash"
        policy = PaymentPolicy.query.filter_by(is_default=True, is_active=True).first()
        if policy:
            _ensure_method_allowed(method, policy)
        if method == "cash" and not _open_shift(employee):
            raise ValueError("افتح وردية الصندوق أولًا")

        visit = ParkVisit(
            customer_id=customer.id,
            visitor_name=visitor_name,
            people_count=people,
            people_remaining=people,
            price_per_person=price_per_person,
            total=total,
            started_at=_now(),
            expected_end_at=expected_end_at,
            status="open",
            created_by_id=current_user.id,
        )
        db.session.add(visit)
        db.session.flush()

        invoice = Invoice(
            number=f"INV-PARK-{uuid4().hex[:10].upper()}",
            customer_id=customer.id,
            booking_id=None,
            issue_date=date.today(),
            status="issued",
            subtotal=total,
            discount=Decimal("0"),
            tax=Decimal("0"),
            total=total,
            paid_amount=Decimal("0"),
            balance_due=total,
            notes_ar=f"دخول الحديقة — {visitor_name} — {people} أشخاص",
        )
        db.session.add(invoice)
        db.session.flush()
        db.session.add(InvoiceLine(
            invoice_id=invoice.id,
            description_ar=f"دخول الحديقة — {visitor_name}",
            quantity=people,
            unit_price=price_per_person,
            line_total=total,
        ))
        db.session.commit()

        payment = record_payment_with_accounting(
            invoice_id=invoice.id,
            amount=total,
            method=method,
            number=f"PAY-PARK-{uuid4().hex[:10].upper()}",
            user_id=current_user.id,
        )
        visit.invoice_id = invoice.id
        db.session.commit()

        return jsonify({
            "ok": True,
            "visit_id": visit.id,
            "visitor_name": visit.visitor_name,
            "people": people,
            "total": str(total),
            "payment": str(payment.amount),
        })
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "تعذر تسجيل دخول الحديقة"}), 409


@bp.post("/park/<int:visit_id>/exit")
@login_required
def park_exit(visit_id):
    employee, error = _require_employee()
    if error:
        return error, 403
    if not _can("staff.park.manage"):
        return jsonify({"error": "لا تملك صلاحية إدارة دخول الحديقة"}), 403

    visit = db.session.get(ParkVisit, visit_id)
    if not visit or visit.status != "open":
        return jsonify({"error": "الدخول غير موجود أو مغلق"}), 404
    try:
        count = int(request.form.get("people_count") or 0)
        if count <= 0:
            raise ValueError("عدد الخارجين غير صحيح")
        if count > visit.people_remaining:
            raise ValueError("عدد الخارجين أكبر من الموجودين حاليًا")
        event = ParkVisitExit(
            visit_id=visit.id,
            people_count=count,
            note_ar=(request.form.get("note_ar") or "").strip() or None,
            created_by_id=current_user.id,
        )
        db.session.add(event)
        visit.people_remaining -= count
        if visit.people_remaining == 0:
            visit.status = "closed"
            visit.closed_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({
            "ok": True,
            "remaining": visit.people_remaining,
            "status": visit.status,
        })
    except (ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400


@bp.get("/finance")
@login_required
def finance():
    employee, error = _require_employee()
    if error:
        return render_template("staff/no_profile.html"), 403
    if not _can("staff.finance.view"):
        return jsonify({"error": "لا تملك صلاحية عرض البيانات المالية"}), 403

    deductions = StaffDeduction.query.filter_by(employee_id=employee.id).order_by(StaffDeduction.deduction_date.desc()).limit(80).all()
    advances = EmployeeAdvance.query.filter_by(employee_id=employee.id).order_by(EmployeeAdvance.issue_date.desc()).limit(80).all()
    payroll = (
        db.session.query(PayrollLine, PayrollRun)
        .join(PayrollRun, PayrollRun.id == PayrollLine.payroll_run_id)
        .filter(PayrollLine.employee_id == employee.id)
        .order_by(PayrollRun.end_date.desc(), PayrollRun.id.desc())
        .limit(24).all()
    )
    shift = _open_shift(employee)
    transactions = (
        CashTransaction.query.filter_by(shift_id=shift.id)
        .order_by(CashTransaction.id.desc()).limit(100).all()
        if shift else []
    )
    return render_template(
        "staff/finance.html",
        employee=employee,
        deductions=deductions,
        advances=advances,
        payroll=payroll,
        shift=shift,
        shift_expected=_shift_expected(shift) if shift else Decimal("0"),
        transactions=transactions,
    )


@bp.get("/attendance")
@login_required
def attendance():
    employee, error = _require_employee()
    if error:
        return render_template("staff/no_profile.html"), 403
    rows = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.work_date.desc()).limit(80).all()
    return render_template("staff/attendance.html", employee=employee, rows=rows)


@bp.get("/availability")
@login_required
def availability():
    employee, error = _require_employee()
    if error:
        return error
    try:
        start_at = _normalize_datetime(request.args.get("start_at"))
        duration = int(request.args.get("duration") or 60)
        if duration <= 0:
            raise ValueError("المدة غير صحيحة")
        end_at = start_at + timedelta(minutes=duration)
    except (ValueError, TypeError):
        return jsonify({"error": "وقت أو مدة غير صحيحة"}), 400

    resources = Resource.query.filter_by(is_active=True).order_by(Resource.sport_id, Resource.id).all()
    busy_ids = {
        row.resource_id
        for row in BookingAllocation.query.filter(
            BookingAllocation.is_active.is_(True),
            BookingAllocation.start_at < end_at,
            BookingAllocation.end_at > start_at,
        ).all()
    }
    blocked_ids = {
        row.resource_id
        for row in ResourceBlock.query.filter(
            ResourceBlock.status == "active",
            ResourceBlock.starts_at < end_at,
            ResourceBlock.ends_at > start_at,
        ).all()
    }
    busy_ids |= blocked_ids
    return jsonify({
        "items": [{
            "id": r.id,
            "name": r.name_ar,
            "busy": r.id in busy_ids,
            "status": r.status,
        } for r in resources]
    })


@bp.post("/cash/open")
@login_required
def cash_open():
    employee, error = _require_employee()
    if error:
        return error, 403
    if _open_shift(employee):
        return jsonify({"error": "لديك وردية مفتوحة بالفعل"}), 400
    try:
        opening = _to_decimal(request.form.get("opening_amount"), "الرصيد الافتتاحي")
        register_id = int(request.form.get("register_id") or 0)
    except (ValueError, TypeError, InvalidOperation):
        return jsonify({"error": "بيانات فتح الوردية غير صحيحة"}), 400
    register = db.session.get(CashRegister, register_id) if register_id else CashRegister.query.filter_by(is_active=True).order_by(CashRegister.id).first()
    if not register or not register.is_active:
        return jsonify({"error": "لا يوجد صندوق نشط"}), 400
    if CashShift.query.filter_by(register_id=register.id, status="open").first():
        return jsonify({"error": "الصندوق مرتبط بورديّة مفتوحة"}), 400
    shift = CashShift(register_id=register.id, employee_id=employee.id, opening_amount=opening, status="open")
    db.session.add(shift)
    db.session.commit()
    return jsonify({"ok": True, "message": "تم فتح الوردية", "shift_id": shift.id})


@bp.post("/cash/close")
@login_required
def cash_close():
    employee, error = _require_employee()
    if error:
        return error, 403
    shift = _open_shift(employee)
    if not shift:
        return jsonify({"error": "لا توجد وردية مفتوحة"}), 400
    try:
        actual = _to_decimal(request.form.get("actual_amount"), "المبلغ الفعلي")
    except (ValueError, TypeError, InvalidOperation):
        return jsonify({"error": "المبلغ الفعلي غير صحيح"}), 400
    expected = _shift_expected(shift)
    shift.expected_amount = expected
    shift.actual_amount = actual
    shift.difference = actual - expected
    shift.status = "closed"
    shift.closed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True, "message": "تم إخلاء العهدة وإغلاق الوردية", "expected": str(expected), "difference": str(shift.difference)})


@bp.get("/api/summary")
@login_required
def api_summary():
    employee, error = _require_employee()
    if error:
        return error
    shift = _open_shift(employee)
    open_visits = ParkVisit.query.filter_by(status="open").all()
    return jsonify({
        "employee": employee.name_ar,
        "shift_open": bool(shift),
        "shift_expected": str(_shift_expected(shift) if shift else 0),
        "park_people": sum(v.people_remaining for v in open_visits),
        "pending_bookings": Booking.query.filter(Booking.status.in_(["hold", "pending"])).count(),
        "active_bookings": Booking.query.filter(Booking.status.in_(["confirmed", "checked_in", "in_progress"])).count(),
    })
