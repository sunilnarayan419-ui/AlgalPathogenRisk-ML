import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.routes import datasets, economics, experiments, models, networks
from app.schemas import BreakEvenRequest, BreakEvenResponse, ExpressionValidationReport
from app.services.economics import calculate_break_even
from app.services.expression import (
    MAX_UPLOAD_BYTES, ExpressionParseError, PayloadTooLargeError, validate_expression_matrix,
)
from app.services.metadata import audit_geo_series_matrix

app = FastAPI(
    title="Algae Culture Vulnerability Prototype",
    version="0.1.0",
    description="Research prototype; no validated culture-collapse prediction model is included."
)
DEFAULT_MATRIX = Path("data/raw/GSE128981_series_matrix.txt")
log = logging.getLogger("app")
for _router in (datasets.router, experiments.router, models.router, networks.router,
                economics.router):
    app.include_router(_router)


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception):
    log.exception("Unhandled error")  # details go to logs, never to the client
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


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


@app.post("/v1/expression-matrices/validate", response_model=ExpressionValidationReport)
async def validate_expression(request: Request):
    """Validate a raw TSV or .tsv.gz body. Reports data quality only; no risk prediction."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes.")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes.")
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        raise HTTPException(status_code=400, detail="Empty request body.")
    try:
        return validate_expression_matrix(raw)
    except PayloadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ExpressionParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
