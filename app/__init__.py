from flask import Flask, redirect, request, url_for
from flask_login import current_user

from .config import Config
from .extensions import csrf, db, login_manager, migrate, socketio


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, message_queue=app.config.get("REDIS_URL"), cors_allowed_origins=app.config.get("SOCKETIO_CORS", []))

    from .models import register_models
    register_models()

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from . import realtime  # noqa: F401

    from .auth.routes import bp as auth_bp
    from .public.routes import bp as public_bp
    from .bookings.routes import bp as bookings_bp
    from .settings.routes import bp as settings_bp
    from .admin.routes import bp as admin_bp
    from .admin.module_routes import bp as module_ui_bp
    from .accounting.routes import bp as accounting_bp
    from .invoices.routes import bp as invoices_bp
    from .payments.routes import bp as payments_bp
    from .cashier.routes import bp as cashier_bp
    from .employees.routes import bp as employees_bp
    from .shifts.routes import bp as shifts_bp
    from .payroll.routes import bp as payroll_bp
    from .maintenance.routes import bp as maintenance_bp
    from .memberships.routes import bp as memberships_bp
    from .packages.routes import bp as packages_bp
    from .training.routes import bp as training_bp
    from .tournaments.routes import bp as tournaments_bp
    from .teams.routes import bp as teams_bp
    from .news.routes import bp as news_bp
    from .offers.routes import bp as offers_bp
    from .ads.routes import bp as ads_bp
    from .live.routes import bp as live_bp
    from .announcements.routes import bp as announcements_bp
    from .notifications.routes import bp as notifications_bp
    from .reports.routes import bp as reports_bp
    from .suppliers.routes import bp as suppliers_bp
    from .inventory.routes import bp as inventory_bp
    from .closing.routes import bp as closing_bp
    from .policies.routes import bp as policies_bp
    from .pricing.routes import bp as pricing_bp
    from .customer.routes import bp as customer_bp
    from .admin.search import bp as admin_search_bp
    from .users.routes import bp as users_bp
    from .staff.routes import bp as staff_bp

    for blueprint in (
        auth_bp, public_bp, bookings_bp, settings_bp, admin_bp, module_ui_bp, admin_search_bp,
        accounting_bp, invoices_bp, payments_bp, cashier_bp, employees_bp,
        shifts_bp, payroll_bp, maintenance_bp, memberships_bp, packages_bp,
        training_bp, tournaments_bp, teams_bp, news_bp, offers_bp, ads_bp,
        live_bp, announcements_bp, notifications_bp, reports_bp, suppliers_bp,
        inventory_bp, closing_bp, policies_bp, pricing_bp, customer_bp, users_bp, staff_bp,
    ):
        app.register_blueprint(blueprint)

    @app.before_request
    def protect_admin_area():
        if not request.path.startswith("/admin"):
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.full_path))
        if current_user.username != "admin" and not current_user.has_permission("admin.access"):
            return {"error": "forbidden", "message": "لا تملك صلاحية دخول لوحة الإدارة"}, 403
        return None

    from .context import inject_site_settings
    app.context_processor(inject_site_settings)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "alkas"}

    return app
