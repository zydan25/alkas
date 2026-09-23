import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import secrets

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..customers.models import Customer
from ..extensions import db
from ..models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(value):
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return None
    return value if value.startswith("/") else None


def _normalize_phone(value):
    return re.sub(r"\D+", "", (value or "").strip())


def _render_register(error=None):
    return render_template(
        "auth/register.html",
        next_url=_safe_next(request.form.get("next") or request.args.get("next")) or "",
        form_data=request.form,
        error=error,
    )


@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(_safe_next(request.args.get("next")) or url_for("public.home"))
    return render_template("auth/login.html", next_url=_safe_next(request.args.get("next")) or "")


@bp.post("/login")
def login_post():
    identifier = (request.form.get("identifier") or "").strip()
    password = request.form.get("password") or ""
    user = User.query.filter(
        (User.username == identifier) | (User.phone == identifier)
    ).first()

    if not user or not user.is_active or not user.check_password(password):
        flash("بيانات الدخول غير صحيحة", "danger")
        return redirect(
            url_for("auth.login", next=_safe_next(request.form.get("next")) or "")
        )

    login_user(user, remember=True)
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(_safe_next(request.form.get("next")) or url_for("public.home"))


@bp.get("/register")
def register():
    if current_user.is_authenticated:
        return redirect(_safe_next(request.args.get("next")) or url_for("public.home"))
    return _render_register()


@bp.post("/register")
def register_post():
    if current_user.is_authenticated:
        return redirect(_safe_next(request.form.get("next")) or url_for("public.home"))

    full_name = re.sub(r"\s+", " ", (request.form.get("full_name") or "").strip())
    phone = _normalize_phone(request.form.get("phone"))
    email = (request.form.get("email") or "").strip().lower() or None
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if len(full_name) < 2:
        return _render_register("أدخل الاسم الكامل.")
    if not 7 <= len(phone) <= 15:
        return _render_register("أدخل رقم هاتف صحيحًا.")
    if email and (len(email) > 180 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        return _render_register("أدخل بريدًا إلكترونيًا صحيحًا أو اتركه فارغًا.")
    if len(password) < 8:
        return _render_register("كلمة المرور يجب أن تكون 8 أحرف على الأقل.")
    if password != password_confirm:
        return _render_register("تأكيد كلمة المرور غير مطابق.")

    if User.query.filter_by(phone=phone).first():
        return _render_register("رقم الهاتف مرتبط بحساب موجود بالفعل.")

    existing_customer = Customer.query.filter_by(phone=phone, is_active=True).first()
    if existing_customer and existing_customer.user_id is not None:
        return _render_register("رقم الهاتف مرتبط بحساب عميل موجود بالفعل.")

    user = User(
        username=f"customer_{secrets.token_hex(8)}",
        display_name=full_name,
        phone=phone,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)

    try:
        db.session.flush()
        if existing_customer:
            existing_customer.user_id = user.id
            existing_customer.name = full_name
            if email:
                existing_customer.email = email
        else:
            db.session.add(
                Customer(
                    user_id=user.id,
                    customer_code=f"CUS-{user.id:08d}",
                    name=full_name,
                    phone=phone,
                    email=email,
                    is_active=True,
                )
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        return _render_register("تعذر إنشاء الحساب الآن. حاول مرة أخرى.")

    login_user(user, remember=True)
    flash("تم إنشاء حسابك بنجاح.", "success")
    return redirect(_safe_next(request.form.get("next")) or url_for("customer.dashboard"))


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.home"))
