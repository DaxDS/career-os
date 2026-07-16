"""Layer 7 — Application tracking, submission metadata, screenshots."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_layer7_tracking"
down_revision: Union[str, None] = "010_layer6_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_applications",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("submission_url", sa.String(length=2000), nullable=False, server_default=""),
    )
    op.add_column(
        "job_applications",
        sa.Column("submission_method", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "job_applications",
        sa.Column("submission_notes", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_job_applications_status", "job_applications", ["status"])

    op.create_table(
        "application_screenshots",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_screenshots_application_id",
        "application_screenshots",
        ["application_id"],
    )

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '7', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("application_screenshots")
    op.drop_index("ix_job_applications_status", table_name="job_applications")
    op.drop_column("job_applications", "submission_notes")
    op.drop_column("job_applications", "submission_method")
    op.drop_column("job_applications", "submission_url")
    op.drop_column("job_applications", "submitted_at")
    op.drop_column("job_applications", "approved_at")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '6', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
