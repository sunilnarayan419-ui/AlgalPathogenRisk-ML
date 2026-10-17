# Testing

```powershell
pytest --cov=app --cov-report=term-missing
ruff check app tests scripts
mkdocs build --strict
```
Layout: `tests/unit` (pure logic), `tests/integration` (SQLite, Alembic), `tests/api` + `tests/test_*_api.py`
(FastAPI TestClient with in-memory SQLite), `tests/scientific_validity` (guardrails). Test data are synthetic and
labelled, except `tests/fixtures/GSE128981_series_matrix.txt` (the real metadata, no expression values).

Coverage includes: GEO parsing (plain/gz/truncated/misaligned), measurement classification, QC flags, log2-FPKM DE
(matches SciPy, BH, batch guard), network analysis, economics (analytic EVPI), ML splits/leakage, artifact
tamper detection, prediction validation, reports, service payload validation, CLIs via subprocess, DB repositories
and API routes.

## Verification status
In the authoring sandbox (no pytest/FastAPI/SQLAlchemy/Alembic) a stand-in runner executed all tests that do not
need those packages: **82 passed**, 0 failed. These modules could not be imported and are **not yet verified**:
`tests/test_api.py`, `tests/test_expression.py`, `tests/test_economics.py`, `tests/api/`, `tests/test_ml_api.py`,
`tests/integration/*`. Run the full suite locally and treat any failure there as a real defect to fix.
