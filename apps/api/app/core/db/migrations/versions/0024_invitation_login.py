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
    with op.batch_alter_table("invitation") as batch:
        batch.alter_column("email", existing_type=sa.String(255), nullable=True)
        batch.add_column(sa.Column("host_kind", sa.String(255), nullable=True))
        batch.add_column(sa.Column("host_login", sa.String(255), nullable=True))
        batch.add_column(sa.Column("team_ids", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("invitation") as batch:
        batch.drop_column("team_ids")
        batch.drop_column("host_login")
        batch.drop_column("host_kind")
        batch.alter_column("email", existing_type=sa.String(255), nullable=False)
