"""WSGI entry point. Gunicorn/production servers point here:
    gunicorn -c gunicorn.conf.py wsgi:app
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "production"))

if __name__ == "__main__":
    app.run()
