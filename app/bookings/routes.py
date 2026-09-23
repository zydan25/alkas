from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from ..extensions import csrf, db
from ..models import Booking, BookingAllocation, BookingMessage, BookingPaymentReceipt, Customer, Resource, ResourceBundle, ResourceBlock, Sport
from ..policies.models import BookingPolicy, PaymentPolicy
from ..settings.services import get_site_settings
from .services import add_to_waitlist, cancel_booking, confirm_booking, create_hold_booking, expand_resource_bundles, expire_holds

bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bp.get("")
def booking_page():
    customer = (
        Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
        if current_user.is_authenticated else None
    )
    resume = session.pop("booking_resume", None)
    now = datetime.now(ZoneInfo("Asia/Aden"))
    # Date defaults to today; start time is intentionally chosen by the customer.
    initial_date = now.date()
    initial_time = request.args.get("time") or ""
    return render_template(
        "bookings/index.html",
        customer=customer,
        sports=Sport.query.filter_by(is_active=True).order_by(Sport.sort_order, Sport.id).all(),
        resources=(
            Resource.query
            .options(selectinload(Resource.sport), selectinload(Resource.zone))
            .filter_by(is_active=True)
            .order_by(Resource.sport_id, Resource.id)
            .all()
        ),
        is_guest=not current_user.is_authenticated,
        resume=resume,
        resume_error=request.args.get("resume_error"),
        initial_sport_id=request.args.get("sport_id", type=int),
        initial_resource_id=request.args.get("resource_id", type=int),
        initial_date=request.args.get("date") or initial_date.isoformat(),
        initial_time=request.args.get("time") or initial_time,
         booking_policy=BookingPolicy.query.filter_by(is_default=True, is_active=True).first(),
        payment_policy=PaymentPolicy.query.filter_by(is_default=True, is_active=True).first(),
        site_settings=get_site_settings(),
    )


@bp.post("/prepare")
def prepare_guest_booking():
    if current_user.is_authenticated:
        return jsonify({"continue_url": url_for("bookings.booking_page")})

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    items = data.get("items") or []

    if len(name) < 2:
        return jsonify({"error": "أدخل اسم العميل أولًا"}), 400
    if len(phone) < 6:
        return jsonify({"error": "أدخل رقم هاتف صحيحًا"}), 400
    if not items:
        return jsonify({"error": "اختر فترة حجز واحدة على الأقل"}), 400

    clean_items = []
    for item in items:
        try:
            resource_ids = [int(value) for value in (item.get("resource_ids") or [])]
            bundle_ids = [int(value) for value in (item.get("bundle_ids") or [])]
            start_at = datetime.fromisoformat(item["start_at"])
            end_at = datetime.fromisoformat(item["end_at"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "بيانات إحدى فترات الحجز غير صحيحة"}), 400
        if not resource_ids and not bundle_ids:
            return jsonify({"error": "اختر ملعبًا أو حزمة لكل فترة"}), 400
        if end_at <= start_at:
            return jsonify({"error": "وقت النهاية يجب أن يكون بعد وقت البداية"}), 400
        clean_items.append({
            "resource_ids": list(dict.fromkeys(resource_ids)),
            "bundle_ids": list(dict.fromkeys(bundle_ids)),
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        })

    session["pending_booking"] = {
        "name": name,
        "phone": phone,
        "email": email[:180],
        "items": clean_items,
    }
    session.modified = True
    return jsonify({"continue_url": url_for("auth.login", next=url_for("bookings.resume"))})


@bp.get("/resume")
@login_required
def resume_guest_booking():
    draft = session.pop("pending_booking", None)
    if not draft:
        return redirect(url_for("bookings.booking_page"))

    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        customer = Customer(
            user_id=current_user.id,
            customer_code=f"CUS-{datetime.now().strftime('%Y%m%d%H%M%S%f')[-10:]}",
            name=draft["name"],
            phone=draft["phone"],
            email=draft.get("email") or None,
            is_active=True,
        )
        db.session.add(customer)
        db.session.flush()
    elif draft.get("email") and not customer.email:
        customer.email = draft["email"]

    try:
        expanded_items = []
        for item in draft["items"]:
            for resource_id in expand_resource_bundles(item.get("resource_ids", []), item.get("bundle_ids", [])):
                expanded_items.append({
                    "resource_id": resource_id,
                    "start_at": item["start_at"],
                    "end_at": item["end_at"],
                })
        if not expanded_items:
            raise ValueError("لم يتم اختيار أي ملعب")
        booking, token = create_hold_booking(
            customer_id=customer.id,
            items=expanded_items,
            source="web",
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return redirect(url_for("bookings.booking_page", resume_error=str(exc)))
    except Exception:
        db.session.rollback()
        return redirect(url_for("bookings.booking_page", resume_error="تعذر إنشاء الحجز؛ ربما حدث تعارض زمني"))

    session["booking_resume"] = {
        "booking_id": booking.id,
        "booking_number": booking.booking_number,
        "hold_token": token,
        "hold_expires_at": booking.hold_expires_at.isoformat(),
    }
    session.modified = True
    return redirect(url_for("bookings.booking_page", resumed="1"))


@bp.get("/resources")
def booking_resources():
    """Return lightweight court data only when the customer opens the picker."""
    query_text = (request.args.get("q") or "").strip()
    sport_id = request.args.get("sport_id", type=int)

    query = (
        Resource.query
        .options(selectinload(Resource.sport), selectinload(Resource.zone))
        .filter(Resource.is_active.is_(True))
    )
    if sport_id:
        query = query.filter(Resource.sport_id == sport_id)
    if query_text:
        like = f"%{query_text}%"
        query = query.filter(
            or_(
                Resource.name_ar.ilike(like),
                Resource.key.ilike(like),
                Sport.name_ar.ilike(like),
            )
        ).join(Sport)

    rows = query.order_by(Resource.sport_id, Resource.id).all()
    return jsonify({
        "items": [
            {
                "id": resource.id,
                "name_ar": resource.name_ar,
                "sport_id": resource.sport_id,
                "sport_name": resource.sport.name_ar if resource.sport else "",
                "sport_icon": resource.sport.icon if resource.sport else "●",
                "zone_name": resource.zone.name_ar if resource.zone else "المرفق الرياضي",
                "image_url": resource.image_url,
                "base_price": str(resource.base_price),
            }
            for resource in rows
        ]
    })


@bp.get("/availability")
def availability():
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    resource_id = request.args.get("resource_id", type=int)
    if not start_raw or not end_raw or not resource_id:
        return jsonify({"error": "start, end, resource_id are required"}), 400

    start_at = datetime.fromisoformat(start_raw)
    end_at = datetime.fromisoformat(end_raw)
    expire_holds()
    conflicts = (
        BookingAllocation.query.join(Booking).filter(
            Booking.status.in_(["hold", "pending", "confirmed", "checked_in", "in_progress"]),
            BookingAllocation.is_active.is_(True),
            BookingAllocation.resource_id == resource_id,
            BookingAllocation.start_at < end_at,
            BookingAllocation.end_at > start_at,
        ).count()
    )
    resource = Resource.query.get_or_404(resource_id)
    blocked = ResourceBlock.query.filter(
        ResourceBlock.resource_id == resource.id,
        ResourceBlock.status == "active",
        ResourceBlock.starts_at < end_at,
        ResourceBlock.ends_at > start_at,
    ).first()
    available = (
        conflicts == 0
        and resource.is_active
        and resource.status == "available"
        and end_at > start_at
        and start_at.astimezone(ZoneInfo("UTC")) >= datetime.now(ZoneInfo("UTC"))
        and not blocked
    )
    return jsonify({
        "available": available,
        "resource_id": resource.id, "start": start_at.isoformat(), "end": end_at.isoformat(),
        "reason": "محجوز" if conflicts else "محجوب" if blocked else "متاح",
    })


@bp.get("/resource/<int:resource_id>")
def resource_detail(resource_id):
    from flask import abort
    from datetime import timedelta
    from ..pricing.services import calculate_price

    resource = Resource.query.get_or_404(resource_id)
    if not resource.is_active:
        abort(404)

    now = datetime.now(ZoneInfo("Asia/Aden"))
    try:
        selected_date = datetime.fromisoformat(request.args.get("date") or now.date().isoformat()).date()
    except ValueError:
        selected_date = now.date()

    slots = []
    current_available = False
    for hour in range(8, 24):
        start = datetime(selected_date.year, selected_date.month, selected_date.day, hour, tzinfo=ZoneInfo("Asia/Aden"))
        end = start + timedelta(hours=1)
        conflict = BookingAllocation.query.join(Booking).filter(
            Booking.status.in_(["hold","pending","confirmed","checked_in","in_progress"]),
            BookingAllocation.is_active.is_(True),
            BookingAllocation.resource_id == resource.id,
            BookingAllocation.start_at < end,
            BookingAllocation.end_at > start,
        ).first()
        blocked = ResourceBlock.query.filter(
            ResourceBlock.resource_id == resource.id,
            ResourceBlock.status == "active",
            ResourceBlock.starts_at < end,
            ResourceBlock.ends_at > start,
        ).first()
        available = (
            resource.status == "available"
            and start >= now
            and not conflict
            and not blocked
        )
        if start <= now < end:
            current_available = available

        slots.append({
            "start": start,
            "end": end,
            "available": available,
            "reason": "محجوز" if conflict else "محجوب" if blocked else ("متاح" if resource.status == "available" else "غير متاح"),
            "price": calculate_price(resource, start, end),
        })

    return render_template(
        "public/resource_detail.html",
        resource=resource,
        slots=slots,
        selected_date=selected_date,
        booking_policy=BookingPolicy.query.filter_by(is_default=True,is_active=True).first(),
        payment_policy=PaymentPolicy.query.filter_by(is_default=True,is_active=True).first(),
        current_available=current_available,
    )


@bp.get("/sport/<int:sport_id>")
def sport_detail(sport_id):
    sport=Sport.query.get_or_404(sport_id)
    resources=Resource.query.filter_by(sport_id=sport.id,is_active=True).order_by(Resource.id).all()
    return render_template("public/sport_detail.html", sport=sport, resources=resources)


@bp.post("/availability/batch")
@csrf.exempt
def availability_batch():
    """Fast pre-check of only the requested booking intervals."""
    data = request.get_json(silent=True) or {}
    raw_items = data.get("items") or []
    if not raw_items:
        return jsonify({"available": True, "items": []})

    parsed = []
    for index, item in enumerate(raw_items):
        try:
            resource_id = int(item["resource_id"])
            start_at = datetime.fromisoformat(item.get("start_at") or item["start"])
            end_at = datetime.fromisoformat(item.get("end_at") or item["end"])
        except (KeyError, TypeError, ValueError):
            parsed.append({
                "index": index,
                "resource_id": item.get("resource_id"),
                "available": False,
                "reason": "بيانات الوقت غير صحيحة",
                "next_available_at": None,
            })
            continue
        parsed.append({
            "index": index,
            "resource_id": resource_id,
            "start": start_at,
            "end": end_at,
        })

    valid = [item for item in parsed if "start" in item]
    if not valid:
        return jsonify({"available": False, "items": parsed})

    resource_ids = list({item["resource_id"] for item in valid})
    resources = {
        resource.id: resource
        for resource in Resource.query.filter(Resource.id.in_(resource_ids)).all()
    }
    min_start = min(item["start"] for item in valid)
    max_end = max(item["end"] for item in valid)
    now_utc = datetime.now(ZoneInfo("UTC"))
    statuses = ["hold", "pending", "confirmed", "checked_in", "in_progress"]

    # Only load allocations that can intersect the requested interval.
    allocations = BookingAllocation.query.join(Booking).filter(
        Booking.status.in_(statuses),
        or_(
            Booking.status != "hold",
            Booking.hold_expires_at.is_(None),
            Booking.hold_expires_at > now_utc,
        ),
        BookingAllocation.is_active.is_(True),
        BookingAllocation.resource_id.in_(resource_ids),
        BookingAllocation.start_at < max_end,
        BookingAllocation.end_at > min_start,
    ).all()
    blocks = ResourceBlock.query.filter(
        ResourceBlock.resource_id.in_(resource_ids),
        ResourceBlock.status == "active",
        ResourceBlock.starts_at < max_end,
        ResourceBlock.ends_at > min_start,
    ).all()

    # First resolve the requested interval using the fast, narrow query.
    nearby_resource_ids = set()
    for item in valid:
        resource = resources.get(item["resource_id"])
        conflict = any(
            x.resource_id == item["resource_id"]
            and x.start_at < item["end"]
            and x.end_at > item["start"]
            for x in allocations
        )
        blocked = any(
            x.resource_id == item["resource_id"]
            and x.starts_at < item["end"]
            and x.ends_at > item["start"]
            for x in blocks
        )
        available = bool(
            resource and resource.is_active and resource.status == "available"
            and item["end"] > item["start"]
            and item["start"].astimezone(ZoneInfo("UTC")) >= now_utc
            and not conflict and not blocked
        )
        item["available"] = available
        item["reason"] = (
            "محجوز" if conflict else
            "محجوب" if blocked else
            "وقت غير صالح" if item["end"] <= item["start"] else
            "وقت منتهٍ" if item["start"].astimezone(ZoneInfo("UTC")) < now_utc else
            "الملعب غير متاح" if not resource or not resource.is_active or resource.status != "available" else
            "متاح"
        )
        item["previous_available_at"] = None
        item["next_available_at"] = None
        if (
            not available
            and resource
            and resource.is_active
            and resource.status == "available"
            and (conflict or blocked)
        ):
            nearby_resource_ids.add(item["resource_id"])

    # Only unavailable resources need the wider look-ahead/look-behind.
    # This keeps the normal availability check fast while keeping nearby times accurate.
    if nearby_resource_ids:
        nearby_min_start = min(
            item["start"] - timedelta(days=1)
            for item in valid
            if item["resource_id"] in nearby_resource_ids
        )
        nearby_max_end = max(
            item["end"] + timedelta(days=7)
            for item in valid
            if item["resource_id"] in nearby_resource_ids
        )
        nearby_allocations = BookingAllocation.query.join(Booking).filter(
            Booking.status.in_(statuses),
            or_(
                Booking.status != "hold",
                Booking.hold_expires_at.is_(None),
                Booking.hold_expires_at > now_utc,
            ),
            BookingAllocation.is_active.is_(True),
            BookingAllocation.resource_id.in_(nearby_resource_ids),
            BookingAllocation.start_at < nearby_max_end,
            BookingAllocation.end_at > nearby_min_start,
        ).all()
        nearby_blocks = ResourceBlock.query.filter(
            ResourceBlock.resource_id.in_(nearby_resource_ids),
            ResourceBlock.status == "active",
            ResourceBlock.starts_at < nearby_max_end,
            ResourceBlock.ends_at > nearby_min_start,
        ).all()

        intervals_by_resource = {}
        for allocation in nearby_allocations:
            intervals_by_resource.setdefault(allocation.resource_id, []).append(
                (allocation.start_at, allocation.end_at)
            )
        for block in nearby_blocks:
            intervals_by_resource.setdefault(block.resource_id, []).append(
                (block.starts_at, block.ends_at)
            )
        for resource_intervals in intervals_by_resource.values():
            resource_intervals.sort(key=lambda pair: pair[0])

        def normalize_forward(value, tz):
            local = value.astimezone(tz).replace(second=0, microsecond=0)
            if local.hour < 8:
                return local.replace(hour=8, minute=0)
            if local.hour > 23 or (local.hour == 23 and local.minute > 30):
                return (local + timedelta(days=1)).replace(hour=8, minute=0)
            return local

        def nearby_free_starts(resource_id, start_at, duration):
            intervals = intervals_by_resource.get(resource_id, [])
            tz = start_at.tzinfo or ZoneInfo("Asia/Aden")
            now_local = now_utc.astimezone(tz)

            # Jump from conflict boundaries instead of checking every minute.
            # This keeps the nearest-time calculation bounded even with many bookings.
            previous = None
            candidate = (start_at - duration).replace(second=0, microsecond=0)
            floor = max(
                now_local.replace(second=0, microsecond=0),
                (start_at - timedelta(days=1)).replace(second=0, microsecond=0),
            )
            while candidate >= floor:
                candidate_end = candidate + duration
                conflicts = [
                    (interval_start, interval_end)
                    for interval_start, interval_end in intervals
                    if interval_start < candidate_end and interval_end > candidate
                ]
                within_hours = (
                    candidate.hour >= 8
                    and candidate.hour <= 23
                    and not (candidate.hour == 23 and candidate.minute > 30)
                )
                if candidate >= now_local and within_hours and not conflicts:
                    previous = candidate
                    break

                if conflicts:
                    candidate = min(interval_start for interval_start, interval_end in conflicts) - duration
                    candidate = candidate.replace(second=0, microsecond=0)
                    continue

                # Skip closed hours in one jump rather than checking every minute.
                if candidate.hour > 23 or (candidate.hour == 23 and candidate.minute > 30):
                    candidate = candidate.replace(hour=23, minute=30)
                elif candidate.hour < 8:
                    candidate = (candidate - timedelta(days=1)).replace(
                        hour=23, minute=30, second=0, microsecond=0
                    )
                else:
                    candidate -= timedelta(minutes=1)

            next_start = normalize_forward(max(start_at, now_utc.astimezone(tz)), tz)
            horizon = next_start + timedelta(days=7)
            while next_start + duration <= horizon:
                conflict_ends = [
                    interval_end
                    for interval_start, interval_end in intervals
                    if interval_start < next_start + duration and interval_end > next_start
                ]
                if not conflict_ends:
                    return previous, next_start
                next_start = normalize_forward(
                    max(next_start + timedelta(minutes=1), max(conflict_ends)),
                    tz,
                )
            return previous, None

        for item in valid:
            if item["resource_id"] not in nearby_resource_ids or item["available"]:
                continue
            previous, next_start = nearby_free_starts(
                item["resource_id"],
                item["start"],
                item["end"] - item["start"],
            )
            item["previous_available_at"] = previous.isoformat() if previous else None
            item["next_available_at"] = next_start.isoformat() if next_start else None

    for item in valid:
        item.pop("start", None)
        item.pop("end", None)

    return jsonify({
        "available": all(item.get("available", False) for item in parsed),
        "items": parsed,
    })


@bp.get("/availability/next")
def availability_next():
    """Find nearby free starts for one court, both before and after the requested slot."""
    resource_id = request.args.get("resource_id", type=int)
    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    if not resource_id or not start_raw or not end_raw:
        return jsonify({"error": "start, end, resource_id are required"}), 400

    try:
        requested_start = datetime.fromisoformat(start_raw)
        requested_end = datetime.fromisoformat(end_raw)
    except ValueError:
        return jsonify({"error": "بيانات الوقت غير صحيحة"}), 400

    if requested_end <= requested_start:
        return jsonify({"next_available_at": None, "previous_available_at": None, "error": "وقت غير صالح"}), 400

    resource = Resource.query.get_or_404(resource_id)
    if not resource.is_active or resource.status != "available":
        return jsonify({
            "next_available_at": None,
            "previous_available_at": None,
            "available": False,
            "reason": "الملعب غير متاح",
        })

    now_utc = datetime.now(ZoneInfo("UTC"))
    duration = requested_end - requested_start
    tz = requested_start.tzinfo or ZoneInfo("Asia/Aden")
    now_local = now_utc.astimezone(tz)
    requested_local = requested_start.astimezone(tz)

    def normalize_forward(value):
        local = value.astimezone(tz).replace(second=0, microsecond=0)
        if local.hour < 8:
            return local.replace(hour=8, minute=0)
        if local.hour > 23 or (local.hour == 23 and local.minute > 30):
            return (local + timedelta(days=1)).replace(hour=8, minute=0)
        return local

    def normalize_backward(value):
        local = value.astimezone(tz).replace(second=0, microsecond=0)
        if local.hour > 23 or (local.hour == 23 and local.minute > 30):
            return local.replace(hour=23, minute=30)
        if local.hour < 8:
            return (local - timedelta(days=1)).replace(hour=23, minute=30)
        return local

    forward_start = normalize_forward(max(requested_start, now_utc.astimezone(tz)))
    backward_start = normalize_backward(requested_start - duration)
    search_floor = max(
        now_utc.astimezone(tz),
        backward_start - timedelta(days=1),
    )
    horizon = forward_start + timedelta(days=7)

    statuses = ["hold", "pending", "confirmed", "checked_in", "in_progress"]
    allocations = BookingAllocation.query.join(Booking).filter(
        Booking.status.in_(statuses),
        or_(
            Booking.status != "hold",
            Booking.hold_expires_at.is_(None),
            Booking.hold_expires_at > now_utc,
        ),
        BookingAllocation.is_active.is_(True),
        BookingAllocation.resource_id == resource.id,
        BookingAllocation.start_at < horizon,
        BookingAllocation.end_at > search_floor,
    ).order_by(BookingAllocation.start_at.asc()).all()
    blocks = ResourceBlock.query.filter(
        ResourceBlock.resource_id == resource.id,
        ResourceBlock.status == "active",
        ResourceBlock.starts_at < horizon,
        ResourceBlock.ends_at > search_floor,
    ).order_by(ResourceBlock.starts_at.asc()).all()

    intervals = [(x.start_at, x.end_at) for x in allocations]
    intervals += [(x.starts_at, x.ends_at) for x in blocks]
    intervals.sort(key=lambda pair: pair[0])

    def is_free(candidate):
        local = candidate.astimezone(tz)
        if local < now_local:
            return False
        if local.hour < 8 or local.hour > 23 or (local.hour == 23 and local.minute > 30):
            return False
        candidate_end = candidate + duration
        return not any(
            interval_start < candidate_end and interval_end > candidate
            for interval_start, interval_end in intervals
        )

    # Latest free start before the requested start. This is deliberately bounded
    # so a card never suggests a distant or stale time.
    previous_available_at = None
    candidate = backward_start
    lower_bound = search_floor.replace(second=0, microsecond=0)
    while candidate >= lower_bound:
        if is_free(candidate) and candidate < requested_start:
            previous_available_at = candidate
            break
        candidate = candidate - timedelta(minutes=1)

    # Earliest free start at or after the requested start.
    next_available_at = None
    candidate = forward_start
    while candidate + duration <= horizon:
        if is_free(candidate):
            next_available_at = candidate
            break
        conflict_ends = [
            interval_end for interval_start, interval_end in intervals
            if interval_start < candidate + duration and interval_end > candidate
        ]
        candidate = normalize_forward(
            max(
                candidate + timedelta(minutes=1),
                max(conflict_ends) if conflict_ends else candidate + timedelta(minutes=1),
            )
        )

    return jsonify({
        "available": False,
        "previous_available_at": previous_available_at.isoformat() if previous_available_at else None,
        "next_available_at": next_available_at.isoformat() if next_available_at else None,
        "reason": "الملعب محجوز أو محجوب في الموعد المحدد",
    })


@bp.post("/quote")
def quote():
    from ..pricing.services import calculate_price
    data = request.get_json(silent=True) or {}
    total = 0
    lines = []
    for item in data.get("items") or []:
        try:
            resource = Resource.query.get(int(item["resource_id"]))
            start_at = datetime.fromisoformat(item["start_at"])
            end_at = datetime.fromisoformat(item["end_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if not resource or not resource.is_active:
            continue
        price = calculate_price(resource, start_at, end_at)
        total += price
        lines.append({
            "resource_id": resource.id,
            "resource": resource.name_ar,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "price": str(price),
        })
    return jsonify({"total": str(total), "lines": lines})


@bp.post("/holds")
@login_required
def create_hold():
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return jsonify({"error": "لا يوجد ملف عميل مرتبط بحسابك"}), 403

    data = request.get_json(silent=True) or {}
    try:
        items = data.get("items")
        if items is None:
            resource_ids = expand_resource_bundles(
                [int(value) for value in data.get("resource_ids", [])],
                [int(value) for value in data.get("bundle_ids", [])],
            )
            start_at = datetime.fromisoformat(data["start_at"])
            end_at = datetime.fromisoformat(data["end_at"])
        else:
            expanded_items = []
            for item in items:
                bundle_ids = [int(v) for v in item.get("bundle_ids", [])]
                expanded = expand_resource_bundles(
                    [int(v) for v in item.get("resource_ids", [])],
                    bundle_ids,
                )
                for resource_id in expanded:
                    expanded_items.append({
                        "resource_id": resource_id,
                        "start_at": item["start_at"],
                        "end_at": item["end_at"],
                    })
            items = expanded_items
            resource_ids = None
            start_at = end_at = None

        booking, token = create_hold_booking(
            customer_id=customer.id,
            resource_ids=resource_ids,
            start_at=start_at,
            end_at=end_at,
            items=items,
            source=data.get("source", "web"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "تعذر إنشاء الحجز؛ ربما يوجد تعارض زمني"}), 409

    return jsonify({
        "booking": {
            "id": booking.id, "number": booking.booking_number, "status": booking.status,
            "payment_status": booking.payment_status, "total": str(booking.total),
            "hold_expires_at": booking.hold_expires_at.isoformat(), "allocations": len(booking.allocations),
        },
        "hold_token": token,
    }), 201


@bp.post("/<int:booking_id>/cancel")
@login_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer or booking.customer_id != customer.id:
        return jsonify({"error": "غير مصرح"}), 403
    try:
        booking, refund = cancel_booking(
            booking_id,
            reason_ar=(request.get_json(silent=True) or {}).get("reason_ar", "إلغاء من العميل"),
            user_id=current_user.id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "booking_id": booking.id,
        "status": booking.status,
        "requested_refund": str(refund),
    })


@bp.get("/<int:booking_id>/messages")
@login_required
def messages(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    staff = current_user.username == "admin" or current_user.has_permission("booking.view")
    if not staff and (not customer or booking.customer_id != customer.id):
        return jsonify({"error":"غير مصرح"}),403
    rows = booking.messages.order_by(BookingMessage.created_at.asc()).all()
    return jsonify([{
        "id": row.id, "sender_role": row.sender_role, "message_type": row.message_type,
        "body_ar": row.body_ar, "attachment_url": row.attachment_url,
        "attachment_name": row.attachment_name, "created_at": row.created_at.isoformat(),
    } for row in rows])


@bp.post("/<int:booking_id>/messages")
@login_required
def send_message(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    staff = current_user.username == "admin" or current_user.has_permission("booking.view")
    if not staff and (not customer or booking.customer_id != customer.id):
        return jsonify({"error":"غير مصرح"}),403

    body = (request.form.get("body_ar") or "").strip()
    attachment = request.files.get("attachment")
    if not body and not (attachment and attachment.filename):
        return jsonify({"error":"اكتب رسالة أو أرفق ملفًا"}),400

    saved = None
    if attachment and attachment.filename:
        try:
            if request.content_length and request.content_length > 12 * 1024 * 1024:
                raise ValueError("حجم المرفق يتجاوز 12 ميجابايت")
            from ..utils.media import save_uploaded_attachment
            saved = save_uploaded_attachment(attachment, f"booking-{booking.id}")
        except ValueError as exc:
            return jsonify({"error":str(exc)}),400

    row = BookingMessage(
        booking_id=booking.id,
        sender_user_id=current_user.id,
        sender_role="staff" if staff else "customer",
        message_type="message",
        body_ar=body or None,
        attachment_url=saved["url"] if saved else None,
        attachment_name=saved["name"] if saved else None,
        attachment_mime=saved["mime"] if saved else None,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({
        "id":row.id, "sender_role":row.sender_role, "body_ar":row.body_ar,
        "attachment_url":row.attachment_url, "attachment_name":row.attachment_name,
        "created_at":row.created_at.isoformat(),
    }),201


@bp.post("/<int:booking_id>/payment-receipt")
@login_required
def payment_receipt(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer or booking.customer_id != customer.id:
        return jsonify({"error":"غير مصرح"}),403
    attachment = request.files.get("receipt")
    if not attachment or not attachment.filename:
        return jsonify({"error":"اختر صورة أو ملف PDF لإشعار الدفع"}),400
    try:
        if request.content_length and request.content_length > 12 * 1024 * 1024:
            raise ValueError("حجم الإشعار يتجاوز 12 ميجابايت")
        from ..utils.media import save_uploaded_attachment
        saved = save_uploaded_attachment(attachment, f"booking-{booking.id}-receipts")
    except ValueError as exc:
        return jsonify({"error":str(exc)}),400

    receipt = BookingPaymentReceipt(
        booking_id=booking.id,
        uploaded_by_id=current_user.id,
        file_url=saved["url"],
        original_name=saved["name"],
        mime_type=saved["mime"],
        status="pending",
    )
    db.session.add(receipt)
    db.session.add(BookingMessage(
        booking_id=booking.id,
        sender_user_id=current_user.id,
        sender_role="customer",
        message_type="payment_receipt",
        body_ar="تم رفع إشعار الدفع للمراجعة.",
        attachment_url=saved["url"],
        attachment_name=saved["name"],
        attachment_mime=saved["mime"],
    ))
    db.session.commit()
    return jsonify({"id":receipt.id,"status":receipt.status,"file_url":receipt.file_url,"message":"تم رفع إشعار الدفع، وحالته الآن قيد المراجعة."}),201


@bp.post("/waitlist")
@login_required
def join_waitlist():
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer:
        return jsonify({"error": "لا يوجد ملف عميل مرتبط بحسابك"}), 403
    data = request.get_json(silent=True) or {}
    try:
        row = add_to_waitlist(
            customer.id,
            int(data["resource_id"]),
            datetime.fromisoformat(data["desired_start_at"]),
            datetime.fromisoformat(data["desired_end_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": row.id, "position": row.position, "status": row.status}), 201


@bp.post("/<int:booking_id>/confirm")
@login_required
def confirm(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    customer = Customer.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not customer or booking.customer_id != customer.id:
        return jsonify({"error": "غير مصرح"}), 403
    try:
        booking, invoice = confirm_booking(booking_id, current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "booking_id": booking.id, "status": booking.status,
        "invoice_id": invoice.id, "invoice_number": invoice.number,
        "total": str(invoice.total), "balance_due": str(invoice.balance_due),
    })
