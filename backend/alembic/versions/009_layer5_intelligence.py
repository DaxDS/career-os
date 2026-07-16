"""Layer 5 — Persisted job scores and agent run history."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_layer5_intelligence"
down_revision: Union[str, None] = "008_layer4_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_scores",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("immigration_score", sa.Integer(), nullable=True),
        sa.Column("pr_score", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("selected_master_resume_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("resume_selection_confidence", sa.Float(), nullable=True),
        sa.Column("immigration_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("ats_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("match_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("selection_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("scoring_method", sa.String(length=50), nullable=False, server_default="llm"),
        sa.Column("agent_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["selected_master_resume_id"], ["master_resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_score_user_job"),
    )
    op.create_index("ix_job_scores_user_id", "job_scores", ["user_id"])
    op.create_index("ix_job_scores_job_id", "job_scores", ["job_id"])
    op.create_index("ix_job_scores_overall_score", "job_scores", ["overall_score"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workflow_type", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("capability", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(length=50), nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_job_id", "agent_runs", ["job_id"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '5', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("job_scores")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '4', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
