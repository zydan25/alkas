from flask import Flask

from .config import Config
from .extensions import csrf, db, login_manager, migrate, socketio


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(
        app,
        message_queue=app.config.get("REDIS_URL"),
        cors_allowed_origins=app.config.get("SOCKETIO_CORS", []),
    )

    from .models import register_models
    register_models()

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .auth.routes import bp as auth_bp
    from .public.routes import bp as public_bp
    from .bookings.routes import bp as bookings_bp
    from .settings.routes import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(settings_bp)

    from .context import inject_site_settings
    app.context_processor(inject_site_settings)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "alkas"}

    return app
