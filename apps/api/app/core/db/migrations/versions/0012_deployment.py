"""deployment: a release arriving at a target, whoever executed it

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deployment",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("app_id", sa.String(length=36), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=255), nullable=False),
        sa.Column("sha", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=False),
        sa.Column("executor", sa.String(length=255), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("ci_run_id", sa.String(length=36), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column(
            "synced_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id", "target", "executor", "external_ref"),
    )


def downgrade() -> None:
    op.drop_table("deployment")
