# Roadmap

**Done and verified (synthetic/metadata only):** GEO parser and audit, exploratory pipeline, log2-FPKM comparison with batch guard,
network analysis, economics with EVPI, ML train/evaluate/predict/report, existing unit tests (82 executed).

**Done but not executed by the authors** (run `pytest`, then treat as working): FastAPI routes, SQL repositories, Alembic 0001-0002,
STRING/BioGRID real-file loading, PyDESeq2 model call, download scripts, Nextflow ML workflow, GitHub Actions.

Next:
- Download and inspect `GSE128981_FPKMs.replicates.v2.tsv.gz`; run `audit_dataset.py` and `run_analysis.py` on it; record the real QC results.
- Raw reads -> counts (nf-core fetchngs/rnaseq for SRP189733; see `count_based_de.md`) for count-based DE.
- Run ruff/mypy/pytest locally; fix findings; generate and commit lockfiles.
- Nextflow: execute and extend (`-stub-run`, then real run); add analysis stages once validated.
- Network enrichment with a proper background universe and multiple-testing correction.
- Outcome-labelled infection/stress experiments -> validated vulnerability model with external validation and calibration.
- Expected-loss / decision-analysis references for the economics module.
