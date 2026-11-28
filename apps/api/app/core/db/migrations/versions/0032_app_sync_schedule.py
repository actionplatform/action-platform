"""app: when the next scheduled sync is due, and when one last found a change

Revision ID: 0032
Revises: 0031
"""

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("app")}

    with op.batch_alter_table("app") as batch:
        if "next_sync_at" not in columns:
            batch.add_column(sa.Column("next_sync_at", sa.DateTime(), nullable=True))

        if "last_change_at" not in columns:
            batch.add_column(sa.Column("last_change_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("app") as batch:
        batch.drop_column("last_change_at")
        batch.drop_column("next_sync_at")
