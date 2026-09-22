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

    from .cli import register_commands
    register_commands(app)

    from .users.models import User

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
    from .customers.routes import bp as customers_bp
    from .admin.search import bp as admin_search_bp
    from .users.routes import bp as users_bp
    from .staff.routes import bp as staff_bp
    from .audit.routes import bp as audit_bp

    for blueprint in (
        auth_bp, public_bp, bookings_bp, settings_bp, admin_bp, module_ui_bp, admin_search_bp,
        accounting_bp, invoices_bp, payments_bp, cashier_bp, employees_bp,
        shifts_bp, payroll_bp, maintenance_bp, memberships_bp, packages_bp,
        training_bp, tournaments_bp, teams_bp, news_bp, offers_bp, ads_bp,
        live_bp, announcements_bp, notifications_bp, reports_bp, suppliers_bp,
        inventory_bp, closing_bp, policies_bp, pricing_bp, customer_bp, customers_bp, users_bp, staff_bp, audit_bp,
    ):
        app.register_blueprint(blueprint)

    ADMIN_PERMISSIONS = [
        ("/admin", "dashboard.view"),
        ("/admin/bookings", "booking.view"),
        ("/admin/customers", "customer.view"),
        ("/admin/resources", "resource.manage"),
        ("/admin/money", "accounting.view"),
        ("/admin/workspace/accounting", "accounting.view"),
        ("/admin/workspace/invoices", "invoice.view"),
        ("/admin/workspace/payments", "payment.view"),
        ("/admin/workspace/cashier", "cashier.manage"),
        ("/admin/workspace/closing", "closing.manage"),
        ("/admin/workspace/employees", "employee.view"),
        ("/admin/workspace/payroll", "payroll.manage"),
        ("/admin/workspace/shifts", "shift.manage"),
        ("/admin/workspace/maintenance", "maintenance.view"),
        ("/admin/workspace/memberships", "membership.manage"),
        ("/admin/workspace/packages", "package.manage"),
        ("/admin/workspace/pricing", "pricing.view"),
        ("/admin/workspace/training", "training.manage"),
        ("/admin/workspace/tournaments", "tournament.manage"),
        ("/admin/workspace/teams", "team.manage"),
        ("/admin/workspace/announcements", "content.manage"),
        ("/admin/workspace/news", "content.manage"),
        ("/admin/workspace/offers", "offer.manage"),
        ("/admin/workspace/ads", "ads.manage"),
        ("/admin/workspace/live", "live.manage"),
        ("/admin/workspace/suppliers", "supplier.manage"),
        ("/admin/workspace/inventory", "inventory.manage"),
        ("/admin/workspace/reports", "reports.view"),
        ("/admin/accounting", "accounting.view"),
        ("/admin/invoices", "invoice.view"),
        ("/admin/payments", "payment.view"),
        ("/admin/cashier", "cashier.manage"),
        ("/admin/closing", "closing.manage"),
        ("/admin/employees", "employee.view"),
        ("/admin/payroll", "payroll.manage"),
        ("/admin/shifts", "shift.manage"),
        ("/admin/maintenance", "maintenance.view"),
        ("/admin/memberships", "membership.manage"),
        ("/admin/packages", "package.manage"),
        ("/admin/pricing", "pricing.view"),
        ("/admin/training", "training.manage"),
        ("/admin/tournaments", "tournament.manage"),
        ("/admin/teams", "team.manage"),
        ("/admin/announcements", "content.manage"),
        ("/admin/news", "content.manage"),
        ("/admin/offers", "offer.manage"),
        ("/admin/ads", "ads.manage"),
        ("/admin/live", "live.manage"),
        ("/admin/suppliers", "supplier.manage"),
        ("/admin/inventory", "inventory.manage"),
        ("/admin/reports", "reports.view"),
        ("/admin/policies", "payment.refund"),
        ("/admin/audit", "audit.view"),
        ("/admin/users", "users.manage"),
        ("/admin/search", "admin.access"),
    ]

    @app.before_request
    def protect_admin_area():
        if not request.path.startswith("/admin"):
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.full_path))
        if current_user.username == "admin":
            return None
        if not current_user.has_permission("admin.access"):
            return {"error": "forbidden", "message": "لا تملك صلاحية دخول لوحة الإدارة"}, 403

        required = "admin.access"
        for prefix, permission in sorted(ADMIN_PERMISSIONS, key=lambda item: len(item[0]), reverse=True):
            if request.path == prefix or request.path.startswith(prefix + "/"):
                required = permission
                break
        if not current_user.has_permission(required):
            return {"error": "forbidden", "message": "لا تملك صلاحية هذه الوحدة"}, 403
        return None

    from .context import inject_site_settings
    app.context_processor(inject_site_settings)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "alkas"}

    return app
