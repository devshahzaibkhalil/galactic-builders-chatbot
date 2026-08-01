"""Serves the embeddable chat widget page.

This is what gets loaded inside the <iframe> on the WordPress site — see
app/templates/widget/widget.html for the actual widget markup/JS, which
talks to /api/chat/message and /api/leads directly from the browser.
"""
from __future__ import annotations

from flask import Blueprint, render_template

widget_routes_bp = Blueprint("widget_routes", __name__)


@widget_routes_bp.get("/")
@widget_routes_bp.get("/chatbot")
def chatbot_page():
    return render_template("widget/widget.html")
