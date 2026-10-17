# AlgalPathogenRisk-ML / Algae Culture Vulnerability Prototype

Research prototype for *Chlamydomonas reinhardtii* transcriptomics: GEO ingestion and QC, exploratory statistics, provenance-tagged
networks, a leakage-safe ML pipeline, a FastAPI backend, SQL provenance storage and hypothetical economic decision support.

## Scientific scope (read first)

The supplied dataset **GEO GSE128981** compares basal transcriptomes of wild-type (Elow47), *srta* mutant (UVM4, UVM11) and complemented
(UVM11-C1/C9) strains (21 samples, RNA-seq; associated paper PMID 33293544 concerns transgene silencing). It has **no infection or culture-collapse
labels**, so this project **makes no pathogen-risk prediction**. The ML pipeline is demonstrated on clearly labelled **synthetic** data; its
scores are uncalibrated and carry no biological meaning. The uploaded series-matrix file has an empty expression table; the FPKM file is
listed in its header and has not been inspected. See `docs/scientific_scope.md`, `docs/limitations.md`, `docs/implementation_status.md`.

## Capabilities (status in `docs/implementation_status.md`)

- GEO series-matrix parser, QC, suitability audit, sample manifest (`app/data/geo.py`, `scripts/audit_*.py`)
- Exploratory analysis (QC, PCA, correlations) and a batch-aware log2-FPKM group comparison with BH FDR (`scripts/run_analysis.py`)
- Optional count-based DE (PyDESeq2) with batch-estimability guards (needs raw counts)
- Experiment design: power, randomization, Welch/BH
- Networks: STRING/BioGRID loaders, descriptive analysis, DE overlay
- ML: grouped splits, baselines, validation-chosen threshold, artifacts with checksums, validated prediction, Markdown reports
- SQL provenance (SQLite default; Alembic) and FastAPI `/api/v1` with `/health` and `/ready`
- Economics: break-even, sensitivity, Monte Carlo + EVPI (hypothetical inputs)

## Install

```powershell
py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

## Data inspection

```powershell
python scripts\audit_geo_matrix.py --input data\raw\GSE128981_series_matrix.txt.gz --manifest-dir data\metadata --gse128981-batch-rule
python scripts\audit_dataset.py --series-matrix data\raw\GSE128981_series_matrix.txt.gz --out reports\audit
python scripts\download_geo.py        # optional, needs network: also fetches the FPKM file
```

## Analysis, ML, API, tests, docs

```powershell
python scripts\run_analysis.py --fpkm data\raw\GSE128981_FPKMs.replicates.v2.tsv.gz --metadata data\metadata\sample_metadata_gsm.csv --out reports\exploratory --contrast UVM4 Elow47 --batch-col batch
python scripts\train_model.py --demo --out models\current --report reports\model_report.json   # SYNTHETIC data
python scripts\make_model_report.py --artifact-dir models\current --out reports\model_report.md
uvicorn app.main:app --reload            # http://127.0.0.1:8000/docs ; try GET /ready
pytest --cov=app
ruff check app tests scripts
mkdocs serve                             # or: mkdocs build --strict
nextflow run workflows/nextflow/main.nf --demo true     # optional; untested
```
Example: `curl -X POST http://127.0.0.1:8000/api/v1/models/train-demo -H "Content-Type: application/json" -d "{\"seed\":1}"`

## Reproducibility and provenance

Explicit seeds; artifacts store config, data hash, software versions and model SHA-256; datasets keyed by SHA-256. Data: NCBI GEO GSE128981
(public; check GEO terms before redistributing files; the repository ships only metadata and a synthetic fixture). Citation: Neupert et al.
2020, Nat Commun 11:6269, doi:10.1038/s41467-020-19983-4. Register: `references/references.json`.

## Current status

Verified in a restricted sandbox: parser, audit, log2-FPKM DE, networks, economics, ML pipeline, docs build, and 82 tests via a stand-in runner.
**Not yet executed:** HTTP routes, SQL/Alembic, Nextflow, CI, ruff/mypy, download scripts, PyDESeq2. Run `pytest` locally and fix findings.
