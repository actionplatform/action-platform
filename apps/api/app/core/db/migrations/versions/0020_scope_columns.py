"""scope: the columns an earlier build wrote and the model no longer has (target_kind, target_options, run_by, url, derived) and app.scopes_seeded go

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

SCOPE_COLUMNS = ("target_kind", "target_options", "run_by", "url", "derived")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    scope = {c["name"] for c in inspector.get_columns("scope")}
    stale = [name for name in SCOPE_COLUMNS if name in scope]

    if stale:
        with op.batch_alter_table("scope") as batch:
            for name in stale:
                batch.drop_column(name)

    if "scopes_seeded" in {c["name"] for c in inspector.get_columns("app")}:
        with op.batch_alter_table("app") as batch:
            batch.drop_column("scopes_seeded")


def downgrade() -> None:
    pass
