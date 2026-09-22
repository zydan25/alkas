from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..models import Permission, Role, User

bp = Blueprint("users", __name__, url_prefix="/admin/users")


def _allowed():
    return current_user.username == "admin" or current_user.has_permission("users.manage")


@bp.get("")
@login_required
def ui():
    if not _allowed():
        return {"error": "forbidden"}, 403
    return render_template(
        "users/index.html",
        users=User.query.order_by(User.id.desc()).limit(100).all(),
        roles=Role.query.order_by(Role.id).all(),
        permissions=Permission.query.filter_by(is_active=True).order_by(Permission.key).all(),
    )
