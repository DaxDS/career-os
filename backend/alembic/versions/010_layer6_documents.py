"""Layer 6 — Job application documents and artifact metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_layer6_documents"
down_revision: Union[str, None] = "009_layer5_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_applications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("master_resume_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="generated"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ats_fact_check_passed", sa.Boolean(), nullable=True),
        sa.Column("generation_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["master_resume_id"], ["master_resumes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )
    op.create_index("ix_job_applications_user_id", "job_applications", ["user_id"])
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"])

    op.create_table(
        "application_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("application_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["job_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "document_type", name="uq_application_doc_type"),
    )
    op.create_index("ix_application_documents_application_id", "application_documents", ["application_id"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '6', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("application_documents")
    op.drop_table("job_applications")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '5', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
