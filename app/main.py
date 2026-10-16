from pathlib import Path
from fastapi import FastAPI, HTTPException
from app.schemas import BreakEvenRequest, BreakEvenResponse
from app.services.economics import calculate_break_even
from app.services.metadata import audit_geo_series_matrix

app = FastAPI(
    title="Algae Culture Vulnerability Prototype",
    version="0.1.0",
    description="Research prototype; no validated culture-collapse prediction model is included."
)
DEFAULT_MATRIX = Path("data/raw/GSE128981_series_matrix.txt")

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "risk_model_loaded": False,
            "biological_validation": "not_established"}

@app.get("/v1/datasets/GSE128981/audit")
def audit_dataset():
    result = audit_geo_series_matrix(DEFAULT_MATRIX)
    if not result["exists"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.post("/v1/economics/break-even", response_model=BreakEvenResponse)
def break_even(request: BreakEvenRequest):
    return calculate_break_even(request)
