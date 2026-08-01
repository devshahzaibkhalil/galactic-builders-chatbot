"""Registers consistent JSON error responses for the whole app. Individual
routes still return their own specific error payloads for expected
failures (validation, permission denied, etc.) — these handlers only catch
what nothing else caught: 404s, 405s, and genuine unhandled exceptions.
"""
from __future__ import annotations

import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("galactic.errors")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "not_found", "message": "The requested resource was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"error": "method_not_allowed", "message": "That method is not allowed here."}), 405

    @app.errorhandler(HTTPException)
    def http_exception(error: HTTPException):
        return jsonify({"error": error.name.lower().replace(" ", "_"), "message": error.description}), error.code

    @app.errorhandler(Exception)
    def unhandled_exception(error: Exception):
        # Full detail goes to the (redacted) structured log; the customer
        # never sees a stack trace or internal exception message.
        logger.exception("Unhandled exception: %s", error)
        return jsonify({
            "error": "internal_server_error",
            "message": "Something went wrong on our end. Please try again.",
        }), 500
