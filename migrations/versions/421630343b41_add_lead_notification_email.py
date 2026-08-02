"""add lead_notification_email to dashboard_settings

Revision ID: 421630343b41
Revises: a6640f53ea52
Create Date: 2026-08-02 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "421630343b41"
down_revision = "a6640f53ea52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_settings",
        sa.Column("lead_notification_email", sa.String(length=254), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dashboard_settings", "lead_notification_email")
