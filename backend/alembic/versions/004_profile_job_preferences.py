"""Layer 1 — Profile fields required by future job matching and immigration layers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_profile_job_preferences"
down_revision: Union[str, None] = "003_layer1_user_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("preferred_provinces", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("preferred_job_categories", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_profiles",
        sa.Column("salary_max_cad", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "salary_max_cad")
    op.drop_column("user_profiles", "preferred_job_categories")
    op.drop_column("user_profiles", "preferred_provinces")
