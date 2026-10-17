"""initial provenance schema (hand-written to mirror app.database.models; not applied by authors)

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table("datasets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("accession", sa.String(32), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("organism", sa.String(128)),
        sa.UniqueConstraint("accession"))
    op.create_table("dataset_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("registered_utc", TS, nullable=False),
        sa.UniqueConstraint("dataset_id", "sha256", name="uq_dataset_sha"))
    op.create_table("data_audits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_version_id", sa.Integer, sa.ForeignKey("dataset_versions.id"), nullable=False),
        sa.Column("valid", sa.Boolean, nullable=False),
        sa.Column("n_genes", sa.Integer, nullable=False),
        sa.Column("n_samples", sa.Integer, nullable=False),
        sa.Column("report", sa.JSON, nullable=False),
        sa.Column("created_utc", TS, nullable=False))
    op.create_table("analysis_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dataset_version_id", sa.Integer, sa.ForeignKey("dataset_versions.id")),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("parameters", sa.JSON, nullable=False),
        sa.Column("seed", sa.Integer),
        sa.Column("software_versions", sa.JSON, nullable=False),
        sa.Column("output_paths", sa.JSON, nullable=False),
        sa.Column("created_utc", TS, nullable=False))
    op.create_table("model_evaluations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("analysis_run_id", sa.Integer, sa.ForeignKey("analysis_runs.id"), nullable=False),
        sa.Column("target", sa.String(128), nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("exploratory", sa.Boolean, nullable=False),
        sa.Column("caveat", sa.Text, nullable=False))
    op.create_table("experiments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("spec", sa.JSON, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_utc", TS, nullable=False),
        sa.UniqueConstraint("name"))
    op.create_table("economic_scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("inputs", sa.JSON, nullable=False),
        sa.Column("outputs", sa.JSON, nullable=False),
        sa.Column("hypothetical", sa.Boolean, nullable=False),
        sa.UniqueConstraint("name"))
    op.create_table("reference_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ref_key", sa.String(64), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("year", sa.Integer),
        sa.Column("url", sa.Text),
        sa.Column("verified", sa.Boolean, nullable=False),
        sa.Column("supports", sa.Text),
        sa.UniqueConstraint("ref_key"))


def downgrade() -> None:
    for t in ("reference_records", "economic_scenarios", "experiments", "model_evaluations",
              "analysis_runs", "data_audits", "dataset_versions", "datasets"):
        op.drop_table(t)
