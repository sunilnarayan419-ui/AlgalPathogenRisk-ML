# Algae Culture Vulnerability — Prototype

Research prototype for *Chlamydomonas reinhardtii* transcriptomics, API delivery, testing, and intervention economics.

## Scientific limitation

GEO GSE128981 compares basal transcriptomes of wild-type, `srta` mutant, and complemented strains. Its metadata does not label infection, stress-induced culture collapse, or production failure. This prototype therefore does **not** claim to predict real culture-collapse risk. A genotype classifier, if later developed, is a different task.

## Quick start (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item "C:\path\to\GSE128981_series_matrix.txt" "data\raw\GSE128981_series_matrix.txt"
python scripts\audit_geo_matrix.py --input data\raw\GSE128981_series_matrix.txt --output reports\geo_metadata_audit.json
pytest
python scripts\audit_geo_matrix.py --input data\raw\GSE128981_series_matrix.txt.gz --manifest-dir data\metadata --gse128981-batch-rule
uvicorn app.main:app --reload
```

Docs/API: `http://127.0.0.1:8000/docs`; documentation: `mkdocs serve`.

## Prototype endpoints

- `GET /health`
- `GET /v1/datasets/GSE128981/audit`
- `POST /v1/economics/break-even`
- `POST /v1/expression-matrices/validate` — send the raw TSV or `.tsv.gz` as the request body (max 25 MB); returns a data-quality report with SHA-256. Assumes genes in rows and samples in columns; this is reported, not verified.

The API intentionally does not emit biological risk probabilities until valid outcome-labelled data and a validated model exist.

## Added in this iteration

Experiment design/power/randomization, Welch+BH analysis, exploratory pipeline (`scripts/run_analysis.py`), grouped ML baseline, evidence-tagged networks, SQLAlchemy provenance, `/api/v1` routes, Docker. See `docs/` and `docs/limitations.md`. Scripts: `scripts/download_geo.py`, `scripts/audit_dataset.py`, `scripts/run_analysis.py`.

## Added in iteration 3 (written, not yet executed)

Alembic migrations (`alembic upgrade head`), mypy config, lockfile tooling (`scripts/lock_dependencies.ps1`), STRING/BioGRID loaders (`scripts/download_interactions.py`, `scripts/build_network.py`), and count-based differential expression with batch-estimability guards (`scripts/run_count_de.py`, needs raw counts). See `docs/count_based_de.md`, `docs/database_migrations.md`, `docs/biological_networks.md`. Declared the missing `SQLAlchemy` dependency.

## Data

The uploaded GEO series matrix contains metadata and an empty expression-table section. GEO lists this supplementary FPKM file; download it and inspect its schema before modelling:
https://ftp.ncbi.nlm.nih.gov/geo/series/GSE128nnn/GSE128981/suppl/GSE128981_FPKMs.replicates.v2.tsv.gz

## Stack decisions

- pandas / NumPy: data validation and processing
- scikit-learn: baseline modelling after labels are defined
- FastAPI / Pydantic: typed API
- pytest: automated tests
- NetworkX: optional interaction/pathway graph analysis
- Nextflow: add when raw FASTQ processing is in scope
- Scrapy: not required for GEO; prefer official GEO/SRA resources or APIs
- MkDocs Material: documentation

## Development sequence

1. Audit data, sample mapping, batches, and expression matrix.
2. Define a valid research baseline (e.g., genotype classification) separately from collapse prediction.
3. Obtain independent stress/infection experiments with measured outcomes.
4. Train and evaluate with splits that prevent replicate/batch leakage.
5. Calibrate on held-out data and use a defensible production prevalence.
6. Evaluate interventions using facility-specific costs and uncertainty.
7. Add external validation, monitoring, model versioning, and operator review.

## References

- GEO GSE128981: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE128981
- Associated PubMed record, PMID 33293544: https://pubmed.ncbi.nlm.nih.gov/33293544/
