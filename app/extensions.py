"""Minimal SQLAlchemy setup shared by all models.

Framework-light (plain SQLAlchemy, not yet wired to Flask-SQLAlchemy) so
models and services are unit-testable without a running Flask app. When
app/__init__.py (the Flask app factory) is built, this Base/engine pair
becomes the backing for Flask-SQLAlchemy's db.session — do not create a
second, parallel ORM setup alongside it.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    return create_engine(database_url, future=True)


def build_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def create_all(engine) -> None:
    """Create tables — used by tests and local SQLite dev only.

    Production schema changes must go through Alembic migrations in
    migrations/versions/, never this call.
    """
    Base.metadata.create_all(engine)
