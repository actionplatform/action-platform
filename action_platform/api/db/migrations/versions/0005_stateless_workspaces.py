"""Checked-out branch per app and pending edits in the database instead of a clone

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registry",
        sa.Column("branch", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_table(
        "draft",
        sa.Column("registry_id", sa.String(length=36), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("registry_id", "path"),
    )


def downgrade() -> None:
    op.drop_table("draft")
    op.drop_column("registry", "branch")
