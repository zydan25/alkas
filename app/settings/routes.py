from flask import Blueprint, abort, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import SiteSetting, SiteTheme
from ..settings.services import get_site_settings

bp = Blueprint("settings", __name__, url_prefix="/settings")


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
        if json_key in data:
            setattr(theme, db_key, str(data[json_key]))

    db.session.commit()
    return jsonify(get_site_settings())
