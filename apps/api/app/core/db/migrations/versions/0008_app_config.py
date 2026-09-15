"""App configuration kept by the platform

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("registry_id", sa.String(length=36), nullable=False),
        sa.Column("data", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("registry_id"),
    )


def downgrade() -> None:
    op.drop_table("app_config")
