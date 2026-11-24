"""invitation: the code-host account's immutable id a login invitation is bound to

Revision ID: 0028
Revises: 0027
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("invitation")}

    if "host_user_id" in columns:
        return

    with op.batch_alter_table("invitation") as batch:
        batch.add_column(sa.Column("host_user_id", sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("invitation") as batch:
        batch.drop_column("host_user_id")
