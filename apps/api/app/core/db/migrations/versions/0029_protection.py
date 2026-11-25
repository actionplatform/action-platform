"""protection: what each app's code host enforces of git-flow, the events that changed it, the organization's default

Revision ID: 0029
Revises: 0028
"""

import sqlalchemy as sa
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()

    if "app_protection" not in tables:
        op.create_table(
            "app_protection",
            sa.Column("app_id", sa.String(length=36), nullable=False),
            sa.Column("state", sa.Text(), nullable=False, server_default="{}"),
            sa.Column(
                "enforced", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("checked_at", sa.DateTime(), nullable=True),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("app_id"),
        )

    if "protection_event" not in tables:
        op.create_table(
            "protection_event",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("app_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=255), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("actor", sa.Text(), nullable=True),
            sa.Column(
                "at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
            sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_protection_event_app_at", "protection_event", ["app_id", "at"]
        )

    if "protection_default" not in tables:
        op.create_table(
            "protection_default",
            sa.Column("organization_id", sa.String(length=36), nullable=False),
            sa.Column(
                "enforce", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["organization_id"], ["organization.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("organization_id"),
        )


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()

    for table in ("protection_default", "protection_event", "app_protection"):
        if table in tables:
            op.drop_table(table)
