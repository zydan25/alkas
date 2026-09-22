import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://alkas:alkas@localhost:5432/alkas",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv("REDIS_URL") or None
    SOCKETIO_CORS = [
        origin.strip()
        for origin in os.getenv("SOCKETIO_CORS", "http://localhost:5000").split(",")
        if origin.strip()
    ]
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Aden")
    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
