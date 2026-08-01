"""Gunicorn config. Usage: gunicorn -c gunicorn.conf.py wsgi:app

Rate limiting (Flask-Limiter) currently uses in-memory storage, which does
not share state across workers — see app/security/rate_limits.py. Running
with more than one worker means each worker enforces its own separate rate
limit window until a shared backend (Redis) is configured there.
"""
import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
