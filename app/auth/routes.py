from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

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
        return redirect(url_for("auth.login"))

    login_user(user, remember=True)
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return redirect(_safe_next(request.form.get("next")) or url_for("public.home"))


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.home"))
