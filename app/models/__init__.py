"""Importing this package registers every ORM model on Base.metadata.

app/__init__.py imports this before calling extensions.create_all() -
otherwise SQLAlchemy only knows about whichever models happened to be
imported by that point (a real bug caught here: the conversations/messages
tables weren't created because conversation_store.py imported their model
lazily, inside a function, after create_all() had already run).
"""
from app.models.admin_user import AdminUser
from app.models.admin_notification import AdminNotification
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.dashboard_setting import DashboardSetting
from app.models.email_notification import EmailNotification
from app.models.feature_event import FeatureEvent
from app.models.lead import Lead, LeadConsent
from app.models.message import Message
from app.models.uploaded_file import UploadedFile
from app.models.unknown_query import UnknownQuery

__all__ = [
    "AdminUser",
    "AdminNotification",
    "Appointment",
    "AuditLog",
    "Conversation",
    "DashboardSetting",
    "EmailNotification",
    "FeatureEvent",
    "Lead",
    "LeadConsent",
    "Message",
    "UploadedFile",
    "UnknownQuery",
]
