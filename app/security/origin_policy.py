"""Restricts which origins receive CORS headers on API responses.

No wildcard ever — an Origin that isn't in the approved list simply gets no
Access-Control-Allow-Origin header, which makes the browser block the
cross-origin JS from reading the response (the request itself may still
hit the server, so this is defense-in-depth alongside CSRF, not a
substitute for it on cookie-authenticated routes).
"""
from __future__ import annotations


def apply_cors_headers(response, request_origin: str | None, allowed_origins: list[str]):
    normalized_allowed = {o.strip() for o in allowed_origins if o.strip()}
    if request_origin and request_origin in normalized_allowed:
        response.headers["Access-Control-Allow-Origin"] = request_origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST"
    return response
