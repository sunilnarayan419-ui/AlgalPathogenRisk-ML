from fastapi import APIRouter, HTTPException

from app.experiments.count_de import ConfoundingError, DesignError
from app.schemas_v1 import DifferentialExpressionRequest
from app.services import analysis_service as svc

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/differential-expression")
def differential_expression(body: DifferentialExpressionRequest):
    """Exploratory OLS on log2(FPKM+1) with BH correction. Not count-based DE; no risk claims."""
    try:
        return svc.de_from_payload(body.model_dump())
    except ConfoundingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (svc.PayloadError, DesignError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
