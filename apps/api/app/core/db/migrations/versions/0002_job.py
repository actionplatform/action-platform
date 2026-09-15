"""job queue

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=255), nullable=False),
        sa.Column(
            "status", sa.String(length=255), server_default="queued", nullable=False
        ),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("app_id", sa.String(length=36), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.Text(), server_default="{}", nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "run_after", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "app_id", "dedupe_key", name="uq_job_dedupe"),
    )


def downgrade() -> None:
    op.drop_table("job")
