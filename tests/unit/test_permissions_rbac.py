import pytest

from app.constants.roles import ADMIN, AGENT, SUPERADMIN
from app.security.permissions import PermissionDeniedError, has_permission, require_permission


def test_agent_can_reply_to_customer():
    assert has_permission(AGENT, "reply_to_customer")


def test_agent_cannot_manage_users():
    assert not has_permission(AGENT, "manage_users")


def test_admin_can_manage_faqs_but_not_manage_users():
    assert has_permission(ADMIN, "manage_faqs")
    assert not has_permission(ADMIN, "manage_users")


def test_superadmin_has_every_permission():
    from app.security.permissions import PERMISSIONS

    for action in PERMISSIONS:
        assert has_permission(SUPERADMIN, action), action


def test_require_permission_raises_for_denied_role():
    with pytest.raises(PermissionDeniedError):
        require_permission(AGENT, "manage_users")


def test_require_permission_passes_for_allowed_role():
    require_permission(ADMIN, "assign_leads")  # should not raise


def test_unknown_action_raises_value_error():
    with pytest.raises(ValueError):
        has_permission(ADMIN, "not_a_real_action")
