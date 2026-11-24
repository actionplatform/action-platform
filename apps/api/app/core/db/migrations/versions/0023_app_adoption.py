"""app_adoption: where each app stands on the way onto the platform, as the last install run found it

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("app_adoption"):
        op.create_table(
            "app_adoption",
            sa.Column("app_id", sa.String(length=36), nullable=False),
            sa.Column("state", sa.String(length=255), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("language", sa.String(length=255), nullable=True),
            sa.Column("ci", sa.String(length=255), nullable=True),
            sa.Column("version", sa.String(length=255), nullable=True),
            sa.Column("branch", sa.String(length=255), nullable=True),
            sa.Column("pull_request_number", sa.Integer(), nullable=True),
            sa.Column("pull_request_url", sa.Text(), nullable=True),
            sa.Column(
                "checked_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("app_id"),
        )


def downgrade() -> None:
    op.drop_table("app_adoption")
