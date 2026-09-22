import re

from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import SiteSetting, SiteTheme
from ..settings.services import get_site_settings

bp = Blueprint("settings", __name__, url_prefix="/settings")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _can_manage():
    return current_user.is_authenticated and (
        current_user.has_permission("settings.manage") or current_user.username == "admin"
    )


@bp.get("/api/public")
def public_settings():
    return jsonify(get_site_settings())


@bp.post("/theme")
@login_required
def save_theme():
    if not _can_manage():
        abort(403)

    data = request.get_json(silent=True) or {}
    theme = SiteTheme.query.filter_by(is_active=True).order_by(SiteTheme.id.desc()).first()
    if not theme:
        theme = SiteTheme(name="default")
        db.session.add(theme)

    allowed = {
        "primary_color": "primary",
        "secondary_color": "secondary",
        "accent_color": "accent",
        "success_color": "success",
        "danger_color": "danger",
        "surface_color": "surface",
        "background_color": "background",
        "text_color": "text",
        "radius": "radius",
    }
    for db_key, json_key in allowed.items():
        if json_key not in data:
            continue
        value = str(data[json_key]).strip()
        if db_key != "radius" and not HEX_RE.fullmatch(value):
            return jsonify({"error": f"قيمة اللون غير صحيحة: {json_key}"}), 400
        setattr(theme, db_key, value)

    version = SiteSetting.query.filter_by(key="asset_version").first()
    if not version:
        version = SiteSetting(key="asset_version", value_type="string", is_public=True)
        db.session.add(version)
    version.value = str(int(version.value or "0") + 1)

    db.session.commit()
    return jsonify(get_site_settings())


@bp.post("/site")
@login_required
def save_site():
    if not _can_manage():
        abort(403)

    data = request.get_json(silent=True) or {}
    allowed = {
        "site_name", "site_short_name", "logo_url", "favicon_url",
        "hero_title", "hero_subtitle", "booking_hold_minutes",
    }
    changed = False

    for key in allowed:
        if key not in data:
            continue
        row = SiteSetting.query.filter_by(key=key).first()
        if not row:
            row = SiteSetting(key=key, value_type="string", is_public=True)
            db.session.add(row)
        row.value = str(data[key])
        changed = True

    if changed:
        version = SiteSetting.query.filter_by(key="asset_version").first()
        if not version:
            version = SiteSetting(key="asset_version", value_type="string", is_public=True, value="1")
            db.session.add(version)
        version.value = str(int(version.value or "0") + 1)

    db.session.commit()
    return jsonify(get_site_settings())
