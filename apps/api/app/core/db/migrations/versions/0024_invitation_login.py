"""invitation: bound to a code-host login when there is no email, and the teams the person joins on accepting

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
    columns = {
        c["name"]: c for c in sa.inspect(op.get_bind()).get_columns("invitation")
    }
    added = [
        sa.Column("host_kind", sa.String(255), nullable=True),
        sa.Column("host_login", sa.String(255), nullable=True),
        sa.Column("team_ids", sa.Text(), nullable=True),
    ]
    missing = [c for c in added if c.name not in columns]

    if not missing and columns["email"]["nullable"]:
        return

    with op.batch_alter_table("invitation") as batch:
        batch.alter_column("email", existing_type=sa.String(255), nullable=True)

        for column in missing:
            batch.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("invitation") as batch:
        batch.drop_column("team_ids")
        batch.drop_column("host_login")
        batch.drop_column("host_kind")
        batch.alter_column("email", existing_type=sa.String(255), nullable=False)
