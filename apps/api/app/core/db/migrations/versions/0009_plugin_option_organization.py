"""Plugin options per organization

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("plugin_option", "plugin_option_old")
    op.create_table(
        "plugin_option",
        sa.Column(
            "organization_id", sa.String(length=36), nullable=False, server_default=""
        ),
        sa.Column("plugin", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default="null"),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("organization_id", "plugin", "key"),
    )
    op.execute(
        "INSERT INTO plugin_option (organization_id, plugin, key, value, updated_at) "
        "SELECT '', plugin, key, value, updated_at FROM plugin_option_old"
    )
    op.drop_table("plugin_option_old")


def downgrade() -> None:
    op.rename_table("plugin_option", "plugin_option_old")
    op.create_table(
        "plugin_option",
        sa.Column("plugin", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default="null"),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("plugin", "key"),
    )
    op.execute(
        "INSERT INTO plugin_option (plugin, key, value, updated_at) "
        "SELECT plugin, key, value, updated_at FROM plugin_option_old WHERE organization_id = ''"
    )
    op.drop_table("plugin_option_old")
