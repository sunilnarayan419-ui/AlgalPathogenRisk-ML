from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import repositories as repo
from app.database.connection import get_db
from app.schemas_v1 import BreakEvenV1, SensitivityRequest
from app.services import economics_core as ec

router = APIRouter(prefix="/api/v1/economics", tags=["economics"])


@router.post("/break-even")
def break_even(body: BreakEvenV1, db: Session = Depends(get_db)):
    out = {"expected_loss_without": ec.expected_loss_without(body.p, body.L),
           "expected_cost_with": ec.expected_cost_with(body.p, body.L, body.C, body.e),
           "net_benefit_per_cycle": ec.net_benefit(body.p, body.L, body.C, body.e),
           "net_benefit_total": ec.net_benefit(body.p, body.L, body.C, body.e, body.cycles),
           "break_even": ec.break_even_probability(body.L, body.C, body.e),
           "assumptions": "Hypothetical inputs; independent identical cycles; p -> p(1-e).",
           "disclaimer": ec.DISCLAIMER}
    if body.save_as:
        try:
            repo.save_scenario(db, body.save_as, body.model_dump(exclude={"save_as"}), out)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return out


@router.post("/sensitivity")
def sensitivity(body: SensitivityRequest):
    if len(body.p_values) * len(body.e_values) > 10000:
        raise HTTPException(status_code=422, detail="Grid too large.")
    try:
        grid = ec.sensitivity_grid(body.L, body.C, body.p_values, body.e_values, body.cycles)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"grid": grid, "disclaimer": ec.DISCLAIMER}
