"""release as the platform's table: component and version per tag, one row per tag, deployments reference it

Revision ID: 0013
Revises: 0012
"""

import re

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

TAG = re.compile(r"^(?:(?P<component>[A-Za-z0-9_.-]+)/)?v?(?P<version>\d.*)$")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    rows = bind.execute(
        sa.text("SELECT id, app_id, tag FROM release ORDER BY synced_at")
    ).fetchall()
    seen: set[tuple[str, str]] = set()

    for id, app_id, tag in rows:
        if (app_id, tag) in seen:
            bind.execute(sa.text("DELETE FROM release WHERE id = :id"), {"id": id})
        else:
            seen.add((app_id, tag))

    release_columns = {c["name"] for c in inspector.get_columns("release")}
    release_uniques = {u["name"] for u in inspector.get_unique_constraints("release")}

    if (
        not {"component", "version"} <= release_columns
        or "uq_release_app_tag" not in release_uniques
    ):
        with op.batch_alter_table("release") as batch:
            if "component" not in release_columns:
                batch.add_column(
                    sa.Column(
                        "component",
                        sa.String(length=255),
                        nullable=False,
                        server_default="",
                    )
                )

            if "version" not in release_columns:
                batch.add_column(
                    sa.Column(
                        "version",
                        sa.String(length=255),
                        nullable=False,
                        server_default="",
                    )
                )

            if "uq_release_app_tag" not in release_uniques:
                batch.create_unique_constraint("uq_release_app_tag", ["app_id", "tag"])

    for id, _, tag in rows:
        found = TAG.match(tag or "")

        if found:
            bind.execute(
                sa.text(
                    "UPDATE release SET component = :c, version = :v WHERE id = :id"
                ),
                {
                    "c": found.group("component") or "",
                    "v": found.group("version"),
                    "id": id,
                },
            )

    deployment_columns = {c["name"] for c in inspector.get_columns("deployment")}

    if "release_id" not in deployment_columns:
        with op.batch_alter_table("deployment") as batch:
            batch.add_column(
                sa.Column("release_id", sa.String(length=36), nullable=True)
            )
            batch.create_foreign_key(
                "fk_deployment_release",
                "release",
                ["release_id"],
                ["id"],
                ondelete="SET NULL",
            )

    bind.execute(
        sa.text(
            "UPDATE deployment SET release_id = ("
            "SELECT r.id FROM release r WHERE r.app_id = deployment.app_id AND r.version = deployment.version "
            "ORDER BY CASE WHEN r.component = '' THEN 0 ELSE 1 END LIMIT 1) "
            "WHERE release_id IS NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("deployment") as batch:
        batch.drop_constraint("fk_deployment_release", type_="foreignkey")
        batch.drop_column("release_id")

    with op.batch_alter_table("release") as batch:
        batch.drop_constraint("uq_release_app_tag", type_="unique")
        batch.drop_column("version")
        batch.drop_column("component")
