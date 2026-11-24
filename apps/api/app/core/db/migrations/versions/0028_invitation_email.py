"""invitation: when the invitation email last went out and why the last send failed

Revision ID: 0028
Revises: 0025
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    present = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("invitation")}
    added = [
        sa.Column("emailed_at", sa.DateTime(), nullable=True),
        sa.Column("email_error", sa.Text(), nullable=True),
    ]

    with op.batch_alter_table("invitation") as batch:
        for column in added:
            if column.name not in present:
                batch.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("invitation") as batch:
        batch.drop_column("email_error")
        batch.drop_column("emailed_at")
