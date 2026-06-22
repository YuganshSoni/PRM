"""Phase 18 notification tables and SMTP config

Revision ID: 2c8f4a1b9e20
Revises: 1abff231cd33
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c8f4a1b9e20"
down_revision: Union[str, None] = "1abff231cd33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_type",
            "dedupe_key",
            "recipient_email",
            name="uq_notification_dedupe",
        ),
    )
    op.create_index(
        op.f("ix_notification_log_notification_type"),
        "notification_log",
        ["notification_type"],
        unique=False,
    )

    op.create_table(
        "timesheet_compliance_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reminder_1_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_2_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_by_manager_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["restored_by_manager_id"], ["resources.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource_id", "week_start", name="uq_compliance_resource_week"
        ),
    )
    op.create_index(
        op.f("ix_timesheet_compliance_records_resource_id"),
        "timesheet_compliance_records",
        ["resource_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_timesheet_compliance_records_week_start"),
        "timesheet_compliance_records",
        ["week_start"],
        unique=False,
    )

    op.add_column(
        "system_config",
        sa.Column("smtp_host", sa.String(length=255), server_default="", nullable=False),
    )
    op.add_column(
        "system_config",
        sa.Column("smtp_port", sa.Integer(), server_default="587", nullable=False),
    )
    op.add_column(
        "system_config",
        sa.Column(
            "smtp_username", sa.String(length=255), server_default="", nullable=False
        ),
    )
    op.add_column(
        "system_config",
        sa.Column(
            "smtp_password", sa.String(length=500), server_default="", nullable=False
        ),
    )
    op.add_column(
        "system_config",
        sa.Column(
            "smtp_from_email", sa.String(length=255), server_default="", nullable=False
        ),
    )
    op.add_column(
        "system_config",
        sa.Column("email_enabled", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("system_config", "email_enabled")
    op.drop_column("system_config", "smtp_from_email")
    op.drop_column("system_config", "smtp_password")
    op.drop_column("system_config", "smtp_username")
    op.drop_column("system_config", "smtp_port")
    op.drop_column("system_config", "smtp_host")
    op.drop_index(
        op.f("ix_timesheet_compliance_records_week_start"),
        table_name="timesheet_compliance_records",
    )
    op.drop_index(
        op.f("ix_timesheet_compliance_records_resource_id"),
        table_name="timesheet_compliance_records",
    )
    op.drop_table("timesheet_compliance_records")
    op.drop_index(
        op.f("ix_notification_log_notification_type"), table_name="notification_log"
    )
    op.drop_table("notification_log")
