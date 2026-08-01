"""Security response headers, applied to every response via after_request.

Restricts iframe embedding to the approved WordPress origins only — no
wildcard frame-ancestors, per spec section 13.
"""
from __future__ import annotations


def apply_security_headers(response, allowed_frame_ancestors: list[str]):
    frame_ancestors = " ".join(a.strip() for a in allowed_frame_ancestors if a.strip()) or "'none'"
    response.headers["Content-Security-Policy"] = f"frame-ancestors {frame_ancestors};"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "0"  # superseded by CSP; explicit disable avoids legacy quirks
    return response
