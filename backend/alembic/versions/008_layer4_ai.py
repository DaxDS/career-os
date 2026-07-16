"""Layer 4 — AI infrastructure metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_layer4_ai"
down_revision: Union[str, None] = "007_job_source_presets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '4', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE system_metadata SET value = '3', updated_at = now() "
            "WHERE key = 'schema_layer'"
        )
    )
