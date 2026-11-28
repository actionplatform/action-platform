"""deployment: the strategy a deployment runs, its steps and its events

Revision ID: 0033
Revises: 0032
"""

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("deployment")}

    with op.batch_alter_table("deployment") as batch:
        if "strategy" not in columns:
            batch.add_column(
                sa.Column(
                    "strategy",
                    sa.String(length=255),
                    nullable=False,
                    server_default="recreate",
                )
            )

        for name in ("strategy_config", "safety", "operations"):
            if name not in columns:
                batch.add_column(sa.Column(name, sa.Text(), nullable=True))

    tables = sa.inspect(bind).get_table_names()

    if "deployment_step" not in tables:
        op.create_table(
            "deployment_step",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("deployment_id", sa.String(length=36), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(length=255), nullable=False),
            sa.Column("params", sa.Text(), nullable=False, server_default="{}"),
            sa.Column(
                "status",
                sa.String(length=255),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("not_before", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("result", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["deployment_id"], ["deployment.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("deployment_id", "position"),
        )
        op.create_index(
            "ix_deployment_step_deployment",
            "deployment_step",
            ["deployment_id", "position"],
        )

    if "deployment_event" not in tables:
        op.create_table(
            "deployment_event",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("deployment_id", sa.String(length=36), nullable=False),
            sa.Column("app_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=255), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("actor", sa.Text(), nullable=True),
            sa.Column(
                "at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            ),
            sa.ForeignKeyConstraint(
                ["deployment_id"], ["deployment.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["app_id"], ["app.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_deployment_event_app_at", "deployment_event", ["app_id", "at"]
        )


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()

    for table in ("deployment_event", "deployment_step"):
        if table in tables:
            op.drop_table(table)

    with op.batch_alter_table("deployment") as batch:
        for name in ("operations", "safety", "strategy_config", "strategy"):
            batch.drop_column(name)
