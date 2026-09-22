from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..utils.media import save_uploaded_media
from .models import Coupon, Offer

bp = Blueprint("offers", __name__, url_prefix="/admin/offers", template_folder="templates")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("offer.manage")


@bp.get("")
@login_required
def ui():
    return render_template(
        "offers/index.html",
        offers=Offer.query.order_by(Offer.priority.desc(), Offer.id.desc()).limit(100).all(),
        coupons=Coupon.query.order_by(Coupon.id.desc()).limit(80).all(),
    )


@bp.get("/new")
@login_required
def new():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return render_template("offers/form.html")


@bp.post("/new")
@login_required
def create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    try:
        title = (request.form.get("title_ar") or "").strip()
        if not title:
            raise ValueError("عنوان العرض مطلوب")
        starts = datetime.fromisoformat(request.form["starts_at"]) if request.form.get("starts_at") else None
        ends = datetime.fromisoformat(request.form["ends_at"]) if request.form.get("ends_at") else None
        if starts and ends and ends <= starts:
            raise ValueError("تاريخ نهاية العرض غير صحيح")

        image_url = save_uploaded_media(request.files.get("image"), "offers", "image")
        db.session.add(
            Offer(
                title_ar=title,
                body_ar=request.form.get("body_ar"),
                image_url=image_url,
                starts_at=starts,
                ends_at=ends,
                discount_percent=request.form.get("discount_percent") or None,
                fixed_discount=request.form.get("fixed_discount") or None,
                status=request.form.get("status", "draft"),
                priority=int(request.form.get("priority") or 0),
            )
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return render_template("offers/form.html", error=str(exc)), 400
    return redirect(url_for("offers.ui"))


@bp.get("/coupon/new")
@login_required
def coupon_new():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return render_template(
        "offers/coupon_form.html",
        offers=Offer.query.order_by(Offer.id.desc()).all(),
    )


@bp.post("/coupon")
@login_required
def coupon_create():
    if not _allowed():
        return {"error": "forbidden"}, 403
    try:
        code = (request.form.get("code") or "").strip().upper()
        if not code:
            raise ValueError("رمز الكوبون مطلوب")
        if Coupon.query.filter_by(code=code).first():
            raise ValueError("الكوبون موجود")
        db.session.add(
            Coupon(
                code=code,
                offer_id=int(request.form["offer_id"]) if request.form.get("offer_id") else None,
                usage_limit=int(request.form["usage_limit"]) if request.form.get("usage_limit") else None,
                valid_from=datetime.fromisoformat(request.form["valid_from"]) if request.form.get("valid_from") else None,
                valid_until=datetime.fromisoformat(request.form["valid_until"]) if request.form.get("valid_until") else None,
            )
        )
        db.session.commit()
    except (KeyError, TypeError, ValueError) as exc:
        db.session.rollback()
        return {"error": str(exc)}, 400
    return redirect(url_for("offers.ui"))


@bp.get("/api")
@login_required
def api():
    return jsonify(
        [
            {"id": o.id, "title_ar": o.title_ar, "status": o.status, "priority": o.priority}
            for o in Offer.query.order_by(Offer.priority.desc(), Offer.id.desc()).limit(50).all()
        ]
    )
