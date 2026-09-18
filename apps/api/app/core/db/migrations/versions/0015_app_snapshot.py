"""app_snapshot: what the app pages read, taken from the clone after every change

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("app_snapshot"):
        op.create_table(
            "app_snapshot",
            sa.Column("registry_id", sa.String(length=36), nullable=False),
            sa.Column("data", sa.Text(), nullable=False, server_default="{}"),
            sa.Column(
                "taken_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
            sa.PrimaryKeyConstraint("registry_id"),
        )


def downgrade() -> None:
    op.drop_table("app_snapshot")
