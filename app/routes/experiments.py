import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import repositories as repo
from app.database.connection import get_db
from app.experiments import analysis as ana
from app.experiments import power as pw
from app.experiments.randomization import randomize
from app.experiments.spec import ExperimentSpec
from app.schemas_v1 import AnalyzeRequest, ExperimentSpecIn, PowerRequest, RandomizeRequest

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.post("/design")
def design(body: ExperimentSpecIn, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"save_as"})
    spec = ExperimentSpec(**data)
    gaps = spec.missing()
    if gaps:
        raise HTTPException(status_code=422, detail={"message": "Incomplete specification; "
                            "define every required item before an inferential design is recommended.",
                            "missing": sorted(set(gaps))})
    plan = spec.to_dict()
    if body.save_as:
        try:
            repo.save_experiment(db, body.save_as, plan)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"spec": plan, "yaml": spec.to_yaml()}


@router.post("/power-analysis")
def power_analysis(body: PowerRequest):
    try:
        if body.endpoint == "continuous":
            if body.effect_size_d is None:
                raise HTTPException(status_code=422, detail="effect_size_d is required.")
            return pw.sample_size("continuous", effect_size_d=body.effect_size_d,
                                  alpha=body.alpha, power=body.power, ratio=body.ratio,
                                  attrition=body.attrition, two_sided=body.two_sided,
                                  n_comparisons=body.n_comparisons)
        if body.endpoint == "binary":
            if body.p1 is None or body.p2 is None:
                raise HTTPException(status_code=422, detail="p1 and p2 are required.")
            return pw.sample_size("binary", p1=body.p1, p2=body.p2, alpha=body.alpha,
                                  power=body.power, ratio=body.ratio, attrition=body.attrition)
        return pw.sample_size(body.endpoint)
    except pw.UnsupportedDesignError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/randomize")
def randomize_units(body: RandomizeRequest):
    try:
        out = randomize(body.unit_ids, body.groups, body.seed, body.blocks)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"seed": body.seed, "method": out.attrs["method"],
            "assignments": out.to_dict(orient="records")}


@router.post("/analyze")
def analyze(body: AnalyzeRequest):
    if len(body.groups) != len(body.values):
        raise HTTPException(status_code=422, detail="values and groups must have equal length.")
    try:
        return ana.two_group_welch(np.asarray(body.values), np.asarray(body.groups), body.group_a,
                                   body.group_b, unit_ids=body.unit_ids, confidence=body.confidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
