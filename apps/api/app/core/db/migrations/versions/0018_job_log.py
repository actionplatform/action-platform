"""job_log: every line a job wrote, stored as it happens so a page can follow the run

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("job_log"):
        return

    op.create_table(
        "job_log",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("line", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_log_job_seq", "job_log", ["job_id", "seq"])


def downgrade() -> None:
    op.drop_index("ix_job_log_job_seq", table_name="job_log")
    op.drop_table("job_log")
