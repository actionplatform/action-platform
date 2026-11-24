"""service_connection: an organization's OAuth connection to a service that is not a code host (Sentry), its tokens sealed

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_connection",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=255), nullable=False),
        sa.Column("login", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("connected_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_service_connection_org_kind",
        "service_connection",
        ["organization_id", "kind"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_service_connection_org_kind", table_name="service_connection")
    op.drop_table("service_connection")
