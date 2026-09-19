"""scope: where an app's releases are deployed, with a kind and a criticality; release.shape: candidate, stable or hotfix

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("scope"):
        op.create_table(
            "scope",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("app_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column(
                "kind", sa.String(length=255), nullable=False, server_default="web"
            ),
            sa.Column(
                "criticality",
                sa.String(length=255),
                nullable=False,
                server_default="low",
            ),
            sa.Column(
                "derived", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("app_id", "name", name="uq_scope_app_name"),
        )
        op.create_index("ix_scope_app_id", "scope", ["app_id"])

    if "shape" not in {c["name"] for c in inspector.get_columns("release")}:
        with op.batch_alter_table("release") as batch:
            batch.add_column(
                sa.Column(
                    "shape",
                    sa.String(length=255),
                    nullable=False,
                    server_default="stable",
                )
            )

        op.execute("UPDATE release SET shape = 'candidate' WHERE version LIKE '%-%'")

    if "scopes_seeded" not in {c["name"] for c in inspector.get_columns("app")}:
        with op.batch_alter_table("app") as batch:
            batch.add_column(
                sa.Column(
                    "scopes_seeded",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade() -> None:
    with op.batch_alter_table("release") as batch:
        batch.drop_column("shape")

    op.drop_index("ix_scope_app_id", table_name="scope")
    op.drop_table("scope")
