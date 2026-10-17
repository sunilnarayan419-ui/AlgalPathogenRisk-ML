from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import repositories as repo
from app.database.connection import get_db
from app.routes._util import read_body_limited
from app.schemas_v1 import DatasetAuditResponse
from app.services import expression as expr

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("")
def list_datasets(db: Session = Depends(get_db)):
    return [{"id": d.id, "accession": d.accession, "n_versions": len(d.versions)}
            for d in repo.list_datasets(db)]


@router.post("/audit", response_model=DatasetAuditResponse)
async def audit_dataset(request: Request, accession: str = "GSE128981",
                        file_name: str = "upload.tsv", db: Session = Depends(get_db)):
    """Body = raw TSV/.tsv.gz. Validates, then records checksum + audit (never stores the matrix)."""
    raw = await read_body_limited(request, expr.MAX_UPLOAD_BYTES)
    try:
        report = expr.validate_expression_matrix(raw)
    except expr.PayloadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except expr.ExpressionParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ds = repo.get_or_create_dataset(db, accession)
    dv = repo.register_version(db, ds, file_name, report.sha256, report.upload_bytes)
    audit = repo.save_audit(db, dv, report.model_dump())
    return DatasetAuditResponse(dataset_version_id=dv.id, audit_id=audit.id, valid=report.valid,
                                sha256=report.sha256, n_genes=report.n_genes,
                                n_samples=report.n_samples,
                                issue_codes=[i.code for i in report.issues])


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = repo.get_dataset(db, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"id": ds.id, "accession": ds.accession,
            "versions": [{"id": v.id, "file_name": v.file_name, "sha256": v.sha256,
                          "size_bytes": v.size_bytes, "n_audits": len(v.audits)}
                         for v in ds.versions]}
