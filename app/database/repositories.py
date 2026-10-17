from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models as m


def get_or_create_dataset(db: Session, accession: str, **fields) -> m.Dataset:
    ds = db.scalar(select(m.Dataset).where(m.Dataset.accession == accession))
    if ds is None:
        ds = m.Dataset(accession=accession, **fields)
        db.add(ds)
        db.flush()
    return ds


def register_version(db: Session, ds: m.Dataset, file_name: str, sha256: str, size: int,
                     source_url: str | None = None) -> m.DatasetVersion:
    """Idempotent on (dataset, checksum): the same bytes are never registered twice."""
    dv = db.scalar(select(m.DatasetVersion).where(
        m.DatasetVersion.dataset_id == ds.id, m.DatasetVersion.sha256 == sha256))
    if dv is None:
        dv = m.DatasetVersion(dataset_id=ds.id, file_name=file_name, sha256=sha256,
                              size_bytes=size, source_url=source_url)
        db.add(dv)
        db.flush()
    return dv


def save_audit(db: Session, dv: m.DatasetVersion, report: dict) -> m.DataAudit:
    audit = m.DataAudit(dataset_version_id=dv.id, valid=bool(report["valid"]),
                        n_genes=report["n_genes"], n_samples=report["n_samples"], report=report)
    db.add(audit)
    db.flush()
    return audit


def list_datasets(db: Session) -> list[m.Dataset]:
    return list(db.scalars(select(m.Dataset).order_by(m.Dataset.accession)))


def get_dataset(db: Session, dataset_id: int) -> m.Dataset | None:
    return db.get(m.Dataset, dataset_id)


def save_experiment(db: Session, name: str, spec: dict) -> m.Experiment:
    if db.scalar(select(m.Experiment).where(m.Experiment.name == name)):
        raise ValueError(f"Experiment '{name}' already exists.")
    exp = m.Experiment(name=name, spec=spec)
    db.add(exp)
    db.flush()
    return exp


def save_scenario(db: Session, name: str, inputs: dict, outputs: dict) -> m.EconomicScenario:
    if db.scalar(select(m.EconomicScenario).where(m.EconomicScenario.name == name)):
        raise ValueError(f"Scenario '{name}' already exists.")
    sc = m.EconomicScenario(name=name, inputs=inputs, outputs=outputs)
    db.add(sc)
    db.flush()
    return sc


def save_run(db: Session, kind: str, parameters: dict, seed: int | None, software: dict,
             dataset_version_id: int | None = None, outputs: dict | None = None) -> m.AnalysisRun:
    run = m.AnalysisRun(kind=kind, parameters=parameters, seed=seed, software_versions=software,
                        dataset_version_id=dataset_version_id, output_paths=outputs or {})
    db.add(run)
    db.flush()
    return run
