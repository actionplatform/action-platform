"""user.disabled_at: an operator turned the account off; it cannot sign in or use its sessions and tokens

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
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("disabled_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user") as batch:
        batch.drop_column("disabled_at")
