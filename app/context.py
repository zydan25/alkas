from flask_login import current_user
from .settings.services import get_site_settings

def can(permission):
    return bool(
        current_user.is_authenticated and (
            current_user.username == "admin" or current_user.has_permission(permission)
        )
    )

def inject_site_settings():
    return {"site_settings": get_site_settings(), "can": can}
