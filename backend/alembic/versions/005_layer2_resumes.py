"""Layer 2 — Master resumes and version history."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_layer2_resumes"
down_revision: Union[str, None] = "004_profile_job_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "master_resumes",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("parsed_content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("role_families", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("classification", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "label", name="uq_master_resume_user_label"),
    )
    op.create_index("ix_master_resumes_user_id", "master_resumes", ["user_id"])

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("master_resume_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("parsed_content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("classification", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["master_resume_id"], ["master_resumes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resume_versions_master_resume_id", "resume_versions", ["master_resume_id"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '2', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("resume_versions")
    op.drop_table("master_resumes")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '1', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
