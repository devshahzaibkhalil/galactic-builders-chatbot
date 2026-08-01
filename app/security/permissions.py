"""Role-based access control — the single place action->role permissions
are defined. Routes and services call has_permission()/require_permission()
rather than checking role strings inline.
"""
from __future__ import annotations

from app.constants.roles import ADMIN, AGENT, SUPERADMIN

# Action name -> roles allowed to perform it. Each role's allowed action set
# is a superset going agent -> admin -> superadmin, matching spec section 14.
PERMISSIONS: dict[str, set[str]] = {
    # Agent
    "view_assigned_conversations": {AGENT, ADMIN, SUPERADMIN},
    "reply_to_customer": {AGENT, ADMIN, SUPERADMIN},
    "add_conversation_note": {AGENT, ADMIN, SUPERADMIN},
    "change_basic_lead_status": {AGENT, ADMIN, SUPERADMIN},
    "take_over_conversation": {AGENT, ADMIN, SUPERADMIN},

    # Admin
    "view_all_leads": {ADMIN, SUPERADMIN},
    "assign_leads": {ADMIN, SUPERADMIN},
    "manage_faqs": {ADMIN, SUPERADMIN},
    "publish_knowledge_update": {ADMIN, SUPERADMIN},
    "view_project_uploads": {ADMIN, SUPERADMIN},
    "resend_failed_notification": {ADMIN, SUPERADMIN},
    "manage_appointments": {ADMIN, SUPERADMIN},
    "manage_appearance": {ADMIN, SUPERADMIN},

    # Superadmin
    "manage_users": {SUPERADMIN},
    "manage_permissions": {SUPERADMIN},
    "configure_notification_recipients": {SUPERADMIN},
    "view_audit_logs": {SUPERADMIN},
    "manage_retention_settings": {SUPERADMIN},
    "manage_system_configuration": {SUPERADMIN},
    "activate_feature_flags": {SUPERADMIN},
}


class PermissionDeniedError(PermissionError):
    def __init__(self, action: str, role: str):
        super().__init__(f"Role '{role}' is not permitted to perform '{action}'.")
        self.action = action
        self.role = role


def has_permission(role: str, action: str) -> bool:
    allowed_roles = PERMISSIONS.get(action)
    if allowed_roles is None:
        raise ValueError(f"Unknown permission action '{action}'.")
    return role in allowed_roles


def require_permission(role: str, action: str) -> None:
    if not has_permission(role, action):
        raise PermissionDeniedError(action, role)
