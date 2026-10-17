# Architecture

```
app/data         GEO parser + QC (geo.py), strict FPKM / raw-count loaders
app/analysis     log2, QC, PCA, exploratory pipeline, log2-FPKM group comparison (de_fpkm.py)
app/experiments  design, power, randomization, Welch, count-based DE (PyDESeq2, optional)
app/networks     provenance-tagged graph, STRING/BioGRID loaders, descriptive analysis + DE overlay
app/ml           baseline.py (genotype baseline + risk status), pipeline.py (train/evaluate/artifact/predict), report.py
app/services     economics_core, analysis_service (pure logic behind routes), legacy prototype services
app/database     SQLAlchemy models/repositories, migrate.py; migrations/ = Alembic
app/routes       versioned FastAPI routers (/api/v1); app/main.py = legacy routes, /health, /ready
scripts/         CLIs: audit, analysis, training, reports, networks, downloads, DB upgrade
workflows/       Nextflow ML workflow (untested)
```
Science code never imports FastAPI. Large matrices, models and graphs stay on disk; SQL stores checksums,
audits, runs, plans, scenarios, model versions and network metadata. The `app/` layout was kept (not moved to `src/`).
