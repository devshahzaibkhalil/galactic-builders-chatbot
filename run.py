"""Local development entry point.

Usage:
    python run.py

For production, use wsgi.py with gunicorn instead — this uses Flask's
built-in dev server, which is not meant to serve real traffic.
"""
import os

from dotenv import load_dotenv

load_dotenv()  # must happen before `from app import create_app` reads any env vars

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=app.config.get("DEBUG", False))
