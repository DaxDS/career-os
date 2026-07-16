"""Layer 0 foundation — audit logging, prompt versioning."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_audit_prompts_foundation"
down_revision: Union[str, None] = "001_layer0_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False, server_default="system"),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_prompt_name_version"),
    )
    op.create_index("ix_prompt_versions_name", "prompt_versions", ["name"])

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '0.1', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_table("audit_logs")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '0', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
