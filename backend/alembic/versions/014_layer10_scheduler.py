"""Layer 10 — Scheduler pipeline runs and notifications."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_layer10_scheduler"
down_revision: Union[str, None] = "013_layer9_browser_automation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("scope_filter", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("step_log", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_runs_user_id", "pipeline_runs", ["user_id"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    op.create_table(
        "pipeline_notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_notifications_user_id", "pipeline_notifications", ["user_id"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '10', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_notifications_user_id", table_name="pipeline_notifications")
    op.drop_table("pipeline_notifications")
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_user_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '9', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
