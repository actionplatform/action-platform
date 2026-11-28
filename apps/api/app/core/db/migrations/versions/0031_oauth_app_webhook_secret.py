"""oauth_app: the sealed secret GitHub signs a manifest App's webhook deliveries with

Revision ID: 0031
Revises: 0030
"""

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("oauth_app")}

    if "webhook_secret_encrypted" not in columns:
        with op.batch_alter_table("oauth_app") as batch:
            batch.add_column(
                sa.Column("webhook_secret_encrypted", sa.Text(), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("oauth_app") as batch:
        batch.drop_column("webhook_secret_encrypted")
