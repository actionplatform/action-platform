"""ci_run.number as a big integer — GitHub Actions run ids do not fit in 32 bits

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ci_run") as batch:
        batch.alter_column(
            "number",
            type_=sa.BigInteger(),
            existing_type=sa.Integer(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("ci_run") as batch:
        batch.alter_column(
            "number",
            type_=sa.Integer(),
            existing_type=sa.BigInteger(),
            existing_nullable=False,
        )
