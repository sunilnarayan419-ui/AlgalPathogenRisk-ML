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


# ------------------------------------------------------------------ runs, models, networks
def create_analysis_run(db: Session, kind: str, parameters: dict, seed: int | None = None,
                        dataset_version_id: int | None = None, software_versions: dict | None = None,
                        output_paths: dict | None = None) -> m.AnalysisRun:
    if not kind:
        raise ValueError("kind is required.")
    run = m.AnalysisRun(kind=kind, parameters=parameters, seed=seed,
                        dataset_version_id=dataset_version_id,
                        software_versions=software_versions or {}, output_paths=output_paths or {})
    db.add(run)
    db.flush()
    return run


def get_analysis_run(db: Session, run_id: int) -> m.AnalysisRun | None:
    return db.get(m.AnalysisRun, run_id)


def save_model_evaluation(db: Session, run: m.AnalysisRun, target: str, metrics: dict,
                          caveat: str, exploratory: bool = True) -> m.ModelEvaluation:
    ev = m.ModelEvaluation(analysis_run_id=run.id, target=target, metrics=metrics,
                           exploratory=exploratory, caveat=caveat)
    db.add(ev)
    db.flush()
    return ev


def register_model_version(db: Session, meta: dict, artifact_path: str) -> m.ModelVersion:
    """Idempotent on the model file checksum. ``meta`` is the artifact's metadata.json."""
    sha = meta["model_sha256"]
    mv = db.scalar(select(m.ModelVersion).where(m.ModelVersion.sha256 == sha))
    if mv is None:
        mv = m.ModelVersion(name=meta["model_name"], sha256=sha, artifact_path=artifact_path,
                            target=meta["target"], synthetic=bool(meta["synthetic"]),
                            calibrated=bool(meta["calibrated"]),
                            feature_schema={"features": meta["features"],
                                            "threshold": meta["threshold"]},
                            metrics=meta["test_metrics"])
        db.add(mv)
        db.flush()
    return mv


def list_model_versions(db: Session) -> list[m.ModelVersion]:
    return list(db.scalars(select(m.ModelVersion).order_by(m.ModelVersion.id.desc())))


def register_network(db: Session, name: str, sources: dict, n_nodes: int, n_edges: int,
                     file_path: str | None = None, file_sha256: str | None = None) -> m.NetworkRecord:
    if db.scalar(select(m.NetworkRecord).where(m.NetworkRecord.name == name)) is not None:
        raise ValueError(f"network {name!r} already registered.")
    rec = m.NetworkRecord(name=name, sources=sources, n_nodes=n_nodes, n_edges=n_edges,
                          file_path=file_path, file_sha256=file_sha256)
    db.add(rec)
    db.flush()
    return rec


def get_network(db: Session, name: str) -> m.NetworkRecord | None:
    return db.scalar(select(m.NetworkRecord).where(m.NetworkRecord.name == name))
