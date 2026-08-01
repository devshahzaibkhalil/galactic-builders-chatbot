"""Application factory. Single place that wires config, the knowledge base,
the database, and blueprints together — routes must never construct their
own KnowledgeService/engine/session, they pull from flask.current_app.extensions.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from app.config import CONFIG_BY_NAME
from app.core.conversation_store import DbConversationStore
from app.core.flow_manager import FlowDefinition, FlowManager, FlowStep
from app.error_handlers import register_error_handlers
from app.extensions import build_engine, build_session_factory, create_all, ensure_schema
from app.logging_config import configure_logging
from app.security.csrf import init_csrf
from app.security.origin_policy import apply_cors_headers
from app.security.rate_limits import init_rate_limits
from app.security.security_headers import apply_security_headers
from app.services.knowledge_service import KnowledgeService
from app.services.storage_service import StorageService

DEFAULT_ESTIMATE_FLOW = FlowDefinition(
    name="estimate_flow",
    steps=[
        FlowStep("service_key", "Which service can the team help with?"),
        FlowStep("project_description", "Tell us a bit about the project."),
        FlowStep("city", "What city is the property in?"),
        FlowStep("state", "What state is that in?"),
        FlowStep("zip_code", "What is the property's ZIP code?"),
        FlowStep("street_address", "What is the street address?", optional=True),
        FlowStep("property_type", "Is this a single-family home, townhome, or something else?"),
        FlowStep("project_stage", "Is this still in the planning stage, or ready to start?"),
        FlowStep("timeline", "What is your preferred project timeline?"),
        FlowStep("budget_range", "What is your approximate budget range?"),
        FlowStep("photo_upload", "Would you like to upload any project photos?", optional=True),
        FlowStep("full_name", "What name should the team use?"),
        FlowStep("email", "What email address should the team use?"),
        FlowStep("phone", "What phone number should the team use?"),
        FlowStep("preferred_contact_method", "How would you prefer the team contact you - email, phone, or text?"),
        FlowStep("best_contact_time", "What is the best time of day to reach you?"),
    ],
)


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME[config_name])

    configure_logging()
    register_error_handlers(app)

    # -- Knowledge base --
    faq_root = Path(__file__).resolve().parent / "data" / "faqs"
    knowledge_service = KnowledgeService(faq_root=faq_root)
    knowledge_service.load(strict=not app.config["TESTING"])
    app.extensions["knowledge_service"] = knowledge_service

    # -- Database (plain SQLAlchemy; see app/extensions.py docstring) --
    from app import models as _models  # noqa: F401 - registers every model on Base.metadata before create_all()

    engine = build_engine(app.config["DATABASE_URL"], app.config["DB_SCHEMA"])
    ensure_schema(engine, app.config["DB_SCHEMA"])
    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = build_session_factory(engine)
    if app.config["TESTING"] or app.config["DATABASE_URL"].startswith("sqlite"):
        create_all(engine)

    # -- Conversation state (persisted via the conversations/messages tables) --
    app.extensions["conversation_store"] = DbConversationStore(app.extensions["db_session_factory"])
    app.extensions["flow_manager"] = FlowManager(DEFAULT_ESTIMATE_FLOW)

    # -- File storage --
    upload_root = Path(app.config.get("UPLOAD_ROOT", "/tmp/galactic_builders_uploads"))
    app.extensions["storage_service"] = StorageService(upload_root)

    # -- Blueprints --
    from app.routes.admin_auth import admin_auth_bp, init_login_manager
    from app.routes.admin_conversations import admin_conversations_bp
    from app.routes.admin_dashboard import admin_dashboard_bp
    from app.routes.admin_leads import admin_leads_bp
    from app.routes.admin_notifications import admin_notifications_bp
    from app.routes.admin_settings import admin_settings_bp
    from app.routes.appointment_api import appointment_api_bp
    from app.routes.chat_api import chat_api_bp
    from app.routes.health_routes import health_bp
    from app.routes.lead_api import lead_api_bp
    from app.routes.upload_api import upload_api_bp
    from app.routes.widget_routes import widget_routes_bp

    init_login_manager(app)
    app.register_blueprint(health_bp)
    app.register_blueprint(widget_routes_bp)
    app.register_blueprint(chat_api_bp)
    app.register_blueprint(lead_api_bp)
    app.register_blueprint(admin_auth_bp)
    app.register_blueprint(upload_api_bp)
    app.register_blueprint(appointment_api_bp)
    app.register_blueprint(admin_conversations_bp)
    app.register_blueprint(admin_leads_bp)
    app.register_blueprint(admin_notifications_bp)
    app.register_blueprint(admin_settings_bp)
    app.register_blueprint(admin_dashboard_bp)

    init_csrf(app)
    init_rate_limits(app)

    @app.after_request
    def _security_headers(response):
        from flask import request as _request
        response = apply_cors_headers(response, _request.headers.get("Origin"), app.config["ALLOWED_ORIGINS"])
        return apply_security_headers(response, app.config["ALLOWED_FRAME_ANCESTORS"])

    return app
