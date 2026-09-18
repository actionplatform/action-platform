"""Indexes on every per-app listing and on the job queue's claim

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_release_app_published", "release", ["app_id", "published_at"]),
    ("ix_pull_request_app_updated", "pull_request", ["app_id", "updated_at"]),
    ("ix_ci_run_app_number", "ci_run", ["app_id", "number"]),
    ("ix_deployment_app_started", "deployment", ["app_id", "started_at"]),
    ("ix_deployment_release", "deployment", ["release_id"]),
    ("ix_job_app_created", "job", ["app_id", "created_at"]),
    ("ix_job_status_run_after", "job", ["status", "run_after"]),
    ("ix_app_project", "app", ["project_id"]),
    ("ix_source_host_org", "source_host", ["organization_id"]),
    ("ix_ci_host_org", "ci_host", ["organization_id"]),
    ("ix_member_user", "member", ["user_id"]),
    ("ix_member_org", "member", ["organization_id"]),
]


def upgrade() -> None:
    present = {
        (table, ix["name"])
        for table in {t for _, t, _ in INDEXES}
        for ix in sa.inspect(op.get_bind()).get_indexes(table)
    }

    for name, table, columns in INDEXES:
        if (table, name) not in present:
            op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
