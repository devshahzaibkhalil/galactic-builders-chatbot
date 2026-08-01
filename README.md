# Galactic Builders Chatbot

Flask backend for the Galactic Project Concierge chatbot: FAQ knowledge base,
lead capture, conversation engine, admin auth/RBAC/MFA, uploads, email, and
more. See inline module docstrings for how each piece fits together.

The project includes the embeddable chat widget, estimate lead-capture flow,
admin dashboard, and SQLite storage. It uses a synchronous request/response
cycle for local development and testing.

## Setup

```powershell
py -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Configure

```powershell
Copy-Item .env.example .env
```

Then fill in `.env`. At minimum, for local development, generate:

```powershell
py -c "import secrets; print(secrets.token_hex(32))"
py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
py -c "import secrets; print(secrets.token_hex(32))"
```

`DATABASE_URL` defaults to a local SQLite file (`sqlite:///galactic_builders_dev.db`)
if left unset in development — no Postgres required to get started.

## Run in VS Code

The repo includes `.vscode/` config, so this should work with no extra setup
beyond installing the Python extension.

1. **Open the folder** in VS Code (`code .` from the project root, or File → Open Folder).
2. **Create the virtual environment from the PowerShell terminal** (View → Terminal):
   ```powershell
   py -m venv venv
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   ```
3. **Select the interpreter**: press `Ctrl+Shift+P`, choose **Python: Select Interpreter**, and select `venv\Scripts\python.exe`. VS Code will prompt to install the Python extension if needed.
4. **Set up `.env`** as described above (`Copy-Item .env.example .env`, fill in the generated keys).
5. **Run it**: open the Run and Debug panel (Cmd/Ctrl+Shift+D) and pick **"Run Flask (run.py)"** from the dropdown, then press the green play button (F5). Set breakpoints in any `app/` file — they'll hit normally since this runs through the debugger, not a subprocess.
   - Use **"Flask (debug mode, auto-reload)"** instead if you want the server to restart automatically on file save.
   - Use **"Create Superadmin"** to run `scripts/create_superadmin.py` with the debugger attached.
6. **Run the tests**: open the Testing panel (flask icon in the sidebar) — pytest should auto-discover everything under `tests/`. Or just run `pytest` in the integrated terminal.

If the interpreter dropdown does not show `venv\Scripts\python.exe`, restart VS Code or choose **Enter interpreter path** and select it manually.

## Run

```bash
python run.py
```

Starts the dev server at `http://127.0.0.1:5000`. On first run it creates the
SQLite file and every table automatically.

Try it:

```bash
curl http://127.0.0.1:5000/health

curl -X POST http://127.0.0.1:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "I want a kitchen remodel", "session_id": "test-1"}'
```

## Create the first admin account

```bash
python scripts/create_superadmin.py
```

Prompts for email/username/password interactively. Then:

```bash
curl -X POST http://127.0.0.1:5000/admin/login \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(curl -s http://127.0.0.1:5000/admin/csrf-token | python3 -c 'import sys,json;print(json.load(sys.stdin)["csrf_token"])')" \
  -c cookies.txt \
  -d '{"username": "your-username", "password": "your-password"}'
```

(Every admin POST route requires an `X-CSRFToken` header — fetch one from
`GET /admin/csrf-token` first, as shown above.)

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest
```

327 tests, no external services required — everything runs against an
in-memory SQLite database.

## Production

```bash
gunicorn -c gunicorn.conf.py wsgi:app
```

Set `FLASK_ENV=production` and a real Postgres `DATABASE_URL` in your
environment first. Note: `Flask-Limiter`'s rate limits currently use in-memory
storage, which does not work correctly across multiple gunicorn workers —
configure a shared backend (Redis) via `storage_uri` in
`app/security/rate_limits.py` before running with more than one worker.

## Project layout

See docstrings throughout `app/` — most modules explain their own
responsibility and what they deliberately don't do. Start with
`app/__init__.py` (the app factory) to see how everything wires together.
