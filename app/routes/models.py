import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from app.ml.baseline import RISK_MODEL_STATUS, evaluate_group_baseline
from app.schemas_v1 import EvaluateRequest

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
