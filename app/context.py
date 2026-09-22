from .settings.services import get_site_settings


def inject_site_settings():
    return {"site_settings": get_site_settings()}
