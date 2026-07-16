"""Layer 9 — Browser automation sessions, runs, and action logs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_layer9_browser_automation"
down_revision: Union[str, None] = "012_layer8_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("connector_key", sa.String(length=100), nullable=False),
        sa.Column("profile_path", sa.String(length=1000), nullable=False),
        sa.Column("storage_state_path", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="idle"),
        sa.Column("browser_name", sa.String(length=50), nullable=False, server_default="chromium"),
        sa.Column("session_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "connector_key", name="uq_browser_session_user_connector"),
    )
    op.create_index("ix_browser_sessions_user_id", "browser_sessions", ["user_id"])

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("browser_session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("connector_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("browser_name", sa.String(length=50), nullable=False, server_default="chromium"),
        sa.Column("stop_before_submit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("submitted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("run_state", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("result_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"]),
        sa.ForeignKeyConstraint(["browser_session_id"], ["browser_sessions.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_runs_user_id", "automation_runs", ["user_id"])
    op.create_index("ix_automation_runs_job_id", "automation_runs", ["job_id"])
    op.create_index("ix_automation_runs_status", "automation_runs", ["status"])

    op.create_table(
        "automation_action_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_action_logs_run_id", "automation_action_logs", ["run_id"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '9', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("automation_action_logs")
    op.drop_table("automation_runs")
    op.drop_table("browser_sessions")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '8', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
