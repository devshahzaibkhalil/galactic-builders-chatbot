#!/usr/bin/env python3
"""Creates the first superadmin account. Run once after setting up the
database:

    python scripts/create_superadmin.py

Prompts for email, username, and password interactively rather than
accepting them as CLI args, so a password never ends up in shell history.
"""
from __future__ import annotations

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.config import CONFIG_BY_NAME  # noqa: E402
from app.constants.roles import SUPERADMIN  # noqa: E402
from app.extensions import build_engine, build_session_factory, create_all  # noqa: E402
from app.services.authentication_service import WeakPasswordError, create_admin_user  # noqa: E402


def main() -> None:
    config = CONFIG_BY_NAME[os.environ.get("FLASK_ENV", "development")]
    engine = build_engine(config.DATABASE_URL)

    import app.models  # noqa: F401 - register all models before create_all

    create_all(engine)
    session = build_session_factory(engine)()

    print("Create the first Galactic Builders superadmin account.\n")
    email = input("Email: ").strip()
    username = input("Username: ").strip()
    password = getpass.getpass("Password (min 12 chars, 3 of: upper/lower/digit/symbol): ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    try:
        user = create_admin_user(session, email=email, username=username, raw_password=password, role=SUPERADMIN)
        session.commit()
    except WeakPasswordError as exc:
        print(f"Password rejected: {exc}")
        sys.exit(1)
    finally:
        session.close()

    print(f"\nSuperadmin '{user.username}' created successfully.")
    print("If MFA is required for this account, enroll it via the admin dashboard after logging in.")


if __name__ == "__main__":
    main()
