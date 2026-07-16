"""Layer 1 — User and profile tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_layer1_user_profile"
down_revision: Union[str, None] = "002_audit_prompts_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("location_city", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("location_province", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("work_authorization", sa.String(length=50), nullable=False, server_default="work_permit"),
        sa.Column("immigration_goals", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("salary_min_cad", sa.Integer(), nullable=True),
        sa.Column("remote_preference", sa.String(length=20), nullable=False, server_default="any"),
        sa.Column("languages", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("linkedin_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '1', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_table("users")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '0.1', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
