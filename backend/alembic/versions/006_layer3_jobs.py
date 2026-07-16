"""Layer 3 — Job import, storage, deduplication, sources."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_layer3_jobs"
down_revision: Union[str, None] = "005_layer2_resumes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_job_source_user_name"),
    )
    op.create_index("ix_job_sources_user_id", "job_sources", ["user_id"])

    op.create_table(
        "job_postings",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("normalized_url", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location_city", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("location_province", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("remote_type", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("description_hash", sa.String(length=64), nullable=False),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("role_family", sa.String(length=50), nullable=True),
        sa.Column("classification", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("is_duplicate_of", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("date_found", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("date_posted", sa.DateTime(timezone=True), nullable=True),
        sa.Column("salary_min_cad", sa.Integer(), nullable=True),
        sa.Column("salary_max_cad", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["is_duplicate_of"], ["job_postings.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["job_sources.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_id", "external_id", name="uq_job_user_source_external"),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_job_user_dedup_key"),
    )
    op.create_index("ix_job_postings_user_id", "job_postings", ["user_id"])
    op.create_index("ix_job_postings_description_hash", "job_postings", ["description_hash"])
    op.create_index("ix_job_postings_dedup_key", "job_postings", ["dedup_key"])
    op.create_index("ix_job_postings_normalized_url", "job_postings", ["normalized_url"])
    op.create_index("ix_job_postings_status", "job_postings", ["status"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '3', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("job_postings")
    op.drop_table("job_sources")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '2', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
