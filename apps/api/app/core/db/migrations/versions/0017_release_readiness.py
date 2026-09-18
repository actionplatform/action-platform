"""release_readiness: whether a release can reach a stage, checked by the worker after every release

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("release_readiness"):
        return

    op.create_table(
        "release_readiness",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("release_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=255), nullable=False),
        sa.Column(
            "status", sa.String(length=255), nullable=False, server_default="queued"
        ),
        sa.Column("ok", sa.Boolean(), nullable=True),
        sa.Column("checks", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["release_id"], ["release.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "stage", name="uq_release_readiness_stage"),
    )
    op.create_index(
        "ix_release_readiness_release_id", "release_readiness", ["release_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_release_readiness_release_id", table_name="release_readiness")
    op.drop_table("release_readiness")
