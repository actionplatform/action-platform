"""worker: the heartbeat each worker process writes, so the API can tell whether anyone is taking jobs

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("worker"):
        op.create_table(
            "worker",
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("kinds", sa.Text(), nullable=False, server_default=""),
            sa.Column("host", sa.String(length=255), nullable=False, server_default=""),
            sa.Column(
                "started_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "last_seen", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
            sa.PrimaryKeyConstraint("name"),
        )


def downgrade() -> None:
    op.drop_table("worker")
