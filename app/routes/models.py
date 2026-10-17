import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import repositories as repo
from app.database.connection import get_db
from app.ml import pipeline as mlp
from app.ml.baseline import RISK_MODEL_STATUS, evaluate_group_baseline
from app.schemas_v1 import DemoTrainRequest, EvaluateRequest, PredictRequest

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/status")
def status():
    """Explicit availability: there is no culture-vulnerability model."""
    return {"risk_model": RISK_MODEL_STATUS,
            "genotype_baseline": "exploratory only; see POST /api/v1/models/evaluate"}


@router.post("/evaluate")
def evaluate(body: EvaluateRequest):
    n = len(body.matrix)
    if n == 0 or len(body.labels) != n or (body.groups is not None and len(body.groups) != n):
        raise HTTPException(status_code=422, detail="matrix, labels and groups must align.")
    if n > 500 or len(body.matrix[0]) > 5000 or len({len(r) for r in body.matrix}) != 1:
        raise HTTPException(status_code=422, detail="matrix must be rectangular, <=500 samples, <=5000 features.")
    try:
        return evaluate_group_baseline(pd.DataFrame(np.asarray(body.matrix, dtype=float)),
                                       body.labels, groups=body.groups, seed=body.seed,
                                       allow_ungrouped=body.allow_ungrouped)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/current")
def current_model():
    """Metadata of the persisted artifact, or 404 if none has been trained."""
    try:
        _, meta = mlp.load_artifact(get_settings().model_dir)
    except mlp.ModelArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {k: meta[k] for k in ("model_name", "created_utc", "features", "target", "threshold",
                                 "synthetic", "calibrated", "test_metrics", "caveats",
                                 "model_sha256")}


@router.post("/train-demo")
def train_demo(body: DemoTrainRequest):
    """Train on SYNTHETIC data and persist the artifact. Software demonstration only."""
    df = mlp.make_demo_dataset(n_groups=body.n_groups, seed=body.seed)
    cfg = mlp.TrainConfig(seed=body.seed, synthetic=True)
    try:
        report = mlp.train_and_evaluate(
            df, cfg, out_dir=get_settings().model_dir,
            dataset_provenance={"source": "synthetic", "generator": "make_demo_dataset"})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"selected_model": report["selected_model"], "test_metrics": report["test_metrics"],
            "caveats": report["caveats"], "artifact_dir": report["artifact_dir"]}


@router.post("/predict")
def predict(body: PredictRequest):
    """Score records against the persisted artifact. Scores are NOT calibrated risk."""
    try:
        return mlp.predict(get_settings().model_dir, body.records)
    except mlp.ModelArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except mlp.FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/register-current")
def register_current(db: Session = Depends(get_db)):
    """Record the current artifact (checksum, schema, metrics) in the database; idempotent."""
    settings = get_settings()
    try:
        _, meta = mlp.load_artifact(settings.model_dir)
    except mlp.ModelArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    mv = repo.register_model_version(db, meta, settings.model_dir)
    return {"id": mv.id, "name": mv.name, "sha256": mv.sha256, "synthetic": mv.synthetic}


@router.get("/versions")
def versions(db: Session = Depends(get_db)):
    return [{"id": v.id, "name": v.name, "sha256": v.sha256, "synthetic": v.synthetic,
             "calibrated": v.calibrated, "created_utc": v.created_utc.isoformat()}
            for v in repo.list_model_versions(db)]
