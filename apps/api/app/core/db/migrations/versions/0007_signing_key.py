"""Signing key for identity tokens

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signing_key",
        sa.Column("kid", sa.String(length=255), nullable=False),
        sa.Column("private_sealed", sa.Text(), nullable=False),
        sa.Column("public_pem", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("kid"),
    )


def downgrade() -> None:
    op.drop_table("signing_key")
