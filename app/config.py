import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # ==========================================================
    # Пути проекта
    # ==========================================================
    BASE_DIR = Path(__file__).resolve().parent.parent

    INSTANCE_DIR = BASE_DIR / "instance"
    UPLOAD_DIR = INSTANCE_DIR / "uploads"
    DATABASE_FILE = INSTANCE_DIR / "catalog.db"

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ==========================================================
    # Flask
    # ==========================================================
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "change-me-please"
    )

    DEBUG = os.getenv(
        "FLASK_DEBUG",
        "0"
    ) == "1"

    # ==========================================================
    # База данных
    # ==========================================================
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        ""
    ).strip()

    if DATABASE_URL:

        # Render / Railway / PostgreSQL
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace(
                "postgres://",
                "postgresql://",
                1
            )

        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    else:
        SQLALCHEMY_DATABASE_URI = (
            f"sqlite:///{DATABASE_FILE.as_posix()}"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }

    # ==========================================================
    # Загрузка файлов
    # ==========================================================
    UPLOAD_FOLDER = str(UPLOAD_DIR)

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # ==========================================================
    # Cookies / Session
    # ==========================================================
    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = os.getenv(
        "SESSION_COOKIE_SAMESITE",
        "Lax"
    )

    SESSION_COOKIE_SECURE = os.getenv(
        "SESSION_COOKIE_SECURE",
        "0"
    ) == "1"

    # ==========================================================
    # CORS
    # ==========================================================
    _cors_origins = os.getenv(
        "CORS_ORIGINS",
        ""
    ).strip()

    if not _cors_origins:

        CORS_ORIGINS = [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:5000",
            "http://localhost:5000"
        ]

    elif _cors_origins == "*":

        CORS_ORIGINS = ["*"]

    else:

        CORS_ORIGINS = [
            origin.strip()
            for origin in _cors_origins.split(",")
            if origin.strip()
        ]

    # ==========================================================
    # CSRF
    # ==========================================================
    WTF_CSRF_TIME_LIMIT = 3600

    # ==========================================================
    # Отладка
    # ==========================================================
    print("\n" + "=" * 80)
    print("CONFIG LOADED")
    print("-" * 80)
    print("BASE_DIR      :", BASE_DIR)
    print("INSTANCE_DIR  :", INSTANCE_DIR)
    print("UPLOAD_DIR    :", UPLOAD_DIR)
    print("DATABASE_FILE :", DATABASE_FILE)
    print("DATABASE_URI  :", SQLALCHEMY_DATABASE_URI)
    print("DEBUG         :", DEBUG)
    print("=" * 80 + "\n")