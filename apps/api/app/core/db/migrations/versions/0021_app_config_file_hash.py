"""app_config.file_hash: the platform.toml last imported from or exported to the clone, so a sync knows when the file changed

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_config") as batch:
        batch.add_column(sa.Column("file_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("app_config") as batch:
        batch.drop_column("file_hash")
