"""oauth_app: the id and sealed private key of a GitHub App created from the manifest

Revision ID: 0030
Revises: 0029
"""

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("oauth_app")}

    with op.batch_alter_table("oauth_app") as batch:
        if "app_id" not in columns:
            batch.add_column(sa.Column("app_id", sa.Text(), nullable=True))

        if "private_key_encrypted" not in columns:
            batch.add_column(
                sa.Column("private_key_encrypted", sa.Text(), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("oauth_app") as batch:
        batch.drop_column("private_key_encrypted")
        batch.drop_column("app_id")
