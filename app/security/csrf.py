"""CSRF protection for the admin dashboard's session-cookie-authenticated
routes.

Public API blueprints (chat_api, lead_api, upload_api, health) are exempt:
they carry no ambient session credential (session_id is an explicit request
field the customer's own client controls, not a cookie the browser attaches
automatically), so cross-site request forgery does not apply to them the
way it does to cookie-authenticated admin actions.
"""
from __future__ import annotations

from flask import Flask
from flask_wtf import CSRFProtect

csrf = CSRFProtect()


def init_csrf(app: Flask) -> None:
    csrf.init_app(app)

    from app.routes.appointment_api import appointment_api_bp
    from app.routes.chat_api import chat_api_bp
    from app.routes.health_routes import health_bp
    from app.routes.lead_api import lead_api_bp
    from app.routes.upload_api import upload_api_bp

    for blueprint in (chat_api_bp, health_bp, lead_api_bp, upload_api_bp, appointment_api_bp):
        csrf.exempt(blueprint)
