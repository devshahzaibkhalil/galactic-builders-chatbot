"""Serves the admin dashboard's HTML pages.

Deliberately separate from the JSON API blueprints (admin_auth, admin_leads,
admin_conversations) and at a distinct URL prefix (/admin/dashboard/...) so
there's no path collision with e.g. GET /admin/leads (JSON). Every page here
is a thin shell — actual data comes from client-side fetch calls against the
existing JSON endpoints, using the shared helpers in
app/static/admin/js/admin.js.
"""
from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/admin/dashboard")


@admin_dashboard_bp.get("/login")
def login_page():
    return render_template("admin/login.html")


@admin_dashboard_bp.get("/forgot-password")
def forgot_password_page():
    return render_template("admin/forgot_password.html")


@admin_dashboard_bp.get("/reset-password")
def reset_password_page():
    return render_template("admin/reset_password.html")


@admin_dashboard_bp.get("/")
@admin_dashboard_bp.get("/leads")
@login_required
def leads_page():
    return render_template("admin/leads.html", active_page="leads")


@admin_dashboard_bp.get("/conversations/<conversation_id>")
@login_required
def conversation_detail_page(conversation_id: str):
    return render_template(
        "admin/conversation_detail.html", active_page="conversations", conversation_id=conversation_id
    )


@admin_dashboard_bp.get("/settings")
@login_required
def settings_page():
    return render_template("admin/settings.html", active_page="settings")
