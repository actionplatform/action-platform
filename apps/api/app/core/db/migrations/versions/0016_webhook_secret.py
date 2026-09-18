"""source_host.webhook_secret_encrypted: the secret deliveries from the host sign with

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("source_host")}

    if "webhook_secret_encrypted" not in columns:
        with op.batch_alter_table("source_host") as batch:
            batch.add_column(
                sa.Column("webhook_secret_encrypted", sa.Text(), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("source_host") as batch:
        batch.drop_column("webhook_secret_encrypted")
