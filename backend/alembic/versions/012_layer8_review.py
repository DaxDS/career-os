"""Layer 8 — Review queue metadata on job applications."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_layer8_review"
down_revision: Union[str, None] = "011_layer7_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_applications",
        sa.Column("review_notes", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "job_applications",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '8', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.drop_column("job_applications", "reviewed_at")
    op.drop_column("job_applications", "review_notes")
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '7', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
