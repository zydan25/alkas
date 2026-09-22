import os

from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "4041"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}

    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True,
    )
