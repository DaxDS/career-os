"""Layer 3 — Built-in job source preset columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_job_source_presets"
down_revision: Union[str, None] = "006_layer3_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_sources",
        sa.Column("preset_key", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "job_sources",
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_job_sources_preset_key", "job_sources", ["preset_key"])
    op.create_unique_constraint(
        "uq_job_source_user_preset_key",
        "job_sources",
        ["user_id", "preset_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_job_source_user_preset_key", "job_sources", type_="unique")
    op.drop_index("ix_job_sources_preset_key", table_name="job_sources")
    op.drop_column("job_sources", "is_builtin")
    op.drop_column("job_sources", "preset_key")
