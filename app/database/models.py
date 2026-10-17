"""Relational provenance schema. Large matrices stay on disk; only paths/checksums/metadata here."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    accession: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str | None] = mapped_column(Text)
    organism: Mapped[str | None] = mapped_column(String(128))
    versions: Mapped[list[DatasetVersion]] = relationship(back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "sha256", name="uq_dataset_sha"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(Text)
    registered_utc: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    dataset: Mapped[Dataset] = relationship(back_populates="versions")
    audits: Mapped[list[DataAudit]] = relationship(back_populates="version")


class DataAudit(Base):
    __tablename__ = "data_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"))
    valid: Mapped[bool] = mapped_column(Boolean)
    n_genes: Mapped[int] = mapped_column(Integer)
    n_samples: Mapped[int] = mapped_column(Integer)
    report: Mapped[dict] = mapped_column(JSON)
    created_utc: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    version: Mapped[DatasetVersion] = relationship(back_populates="audits")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_version_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_versions.id"))
    kind: Mapped[str] = mapped_column(String(64))
    parameters: Mapped[dict] = mapped_column(JSON)
    seed: Mapped[int | None] = mapped_column(Integer)
    software_versions: Mapped[dict] = mapped_column(JSON)
    output_paths: Mapped[dict] = mapped_column(JSON, default=dict)
    created_utc: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"))
    target: Mapped[str] = mapped_column(String(128))
    metrics: Mapped[dict] = mapped_column(JSON)
    exploratory: Mapped[bool] = mapped_column(Boolean, default=True)  # never externally validated here
    caveat: Mapped[str] = mapped_column(Text)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    spec: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="planned_not_executed")
    created_utc: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EconomicScenario(Base):
    __tablename__ = "economic_scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    outputs: Mapped[dict] = mapped_column(JSON)
    hypothetical: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceRecord(Base):
    __tablename__ = "reference_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    ref_key: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    supports: Mapped[str | None] = mapped_column(Text)
