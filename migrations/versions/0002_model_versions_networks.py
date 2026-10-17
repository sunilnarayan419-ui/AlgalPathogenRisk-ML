"""model_versions and network_records (hand-written; not applied by authors)

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table("model_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("artifact_path", sa.Text, nullable=False),
        sa.Column("target", sa.String(128), nullable=False),
        sa.Column("synthetic", sa.Boolean, nullable=False),
        sa.Column("calibrated", sa.Boolean, nullable=False),
        sa.Column("feature_schema", sa.JSON, nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("created_utc", TS, nullable=False),
        sa.UniqueConstraint("sha256"))
    op.create_table("network_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sources", sa.JSON, nullable=False),
        sa.Column("n_nodes", sa.Integer, nullable=False),
        sa.Column("n_edges", sa.Integer, nullable=False),
        sa.Column("file_path", sa.Text),
        sa.Column("file_sha256", sa.String(64)),
        sa.Column("created_utc", TS, nullable=False),
        sa.UniqueConstraint("name"))


def downgrade() -> None:
    op.drop_table("network_records")
    op.drop_table("model_versions")
