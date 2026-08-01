"""Minimal SQLAlchemy setup shared by all models.

Framework-light (plain SQLAlchemy, not yet wired to Flask-SQLAlchemy) so
models and services are unit-testable without a running Flask app. When
app/__init__.py (the Flask app factory) is built, this Base/engine pair
becomes the backing for Flask-SQLAlchemy's db.session — do not create a
second, parallel ORM setup alongside it.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str, schema: str = "public"):
    """Build the engine. When schema is anything other than 'public' (i.e.
    this app is sharing a Postgres database with another app), connections
    are pinned to that schema via search_path so every table this app
    creates or queries lives there instead of colliding with another app's
    tables of the same name in 'public'."""
    connect_args = {}
    if not database_url.startswith("sqlite") and schema != "public":
        connect_args["options"] = f"-csearch_path={schema},public"
    return create_engine(database_url, future=True, connect_args=connect_args)


def ensure_schema(engine, schema: str) -> None:
    """Create the dedicated schema if it doesn't exist yet. No-op for the
    default 'public' schema or for SQLite (which has no schema concept)."""
    if schema == "public" or engine.url.get_backend_name() == "sqlite":
        return
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()


def build_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def create_all(engine) -> None:
    """Create tables — used by tests and local SQLite dev only.

    Production schema changes must go through Alembic migrations in
    migrations/versions/, never this call.
    """
    Base.metadata.create_all(engine)
