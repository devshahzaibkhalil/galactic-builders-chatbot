"""Application configuration.

Real secrets come from environment variables (see .env.example) — nothing
here is a usable default in production. DevelopmentConfig/TestingConfig
exist so this phase can run and be tested without a real Postgres/Redis.
"""
from __future__ import annotations

import os


def _normalized_database_url() -> str:
    """Render and Railway both inject DATABASE_URL with the legacy
    'postgres://' scheme, which SQLAlchemy 1.4+/2.x rejects outright
    (NoSuchModuleError). Rewrite it to 'postgresql://' so the same env
    var works unmodified on either platform."""
    url = os.environ.get("DATABASE_URL", "sqlite:///galactic_builders_dev.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    DATABASE_URL = _normalized_database_url()
    # When sharing a Postgres database with another app, set DB_SCHEMA to
    # keep this app's tables (and its alembic version table) fully isolated
    # in their own schema instead of colliding with the default 'public'
    # schema. Defaults to 'public' so single-app / local SQLite setups are
    # unaffected.
    DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "https://galacticbuilldersllc.com,https://www.galacticbuilldersllc.com",
    ).split(",")
    ALLOWED_FRAME_ANCESTORS = os.environ.get(
        "ALLOWED_FRAME_ANCESTORS",
        "https://galacticbuilldersllc.com,https://www.galacticbuilldersllc.com",
    ).split(",")
    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    DATABASE_URL = "sqlite:///galactic_builders_dev.db"
    SESSION_COOKIE_SECURE = False  # local HTTP only
    DEBUG = True


class TestingConfig(BaseConfig):
    SECRET_KEY = "test-secret-key-not-for-production"
    DATABASE_URL = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE = False
    TESTING = True


class ProductionConfig(BaseConfig):
    pass


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
