# Implementation status

Legend: **Verified** = executed in the authoring sandbox (Python 3.12, pandas/NumPy/SciPy/scikit-learn/NetworkX,
no pytest/FastAPI/SQLAlchemy/network) • **Written** = code and tests exist but were not executed there •
**Partial** • **Future**.

| Area | Component | Status |
|---|---|---|
| Data | GEO series-matrix parser, QC, suitability (`app/data/geo.py`) | Verified (real metadata + synthetic tables) |
| Data | Strict FPKM / raw-count loaders | Verified (existing unit tests executed) |
| Data | Download scripts (`download_geo.py`, `download_interactions.py`) | Written (need network) |
| Analysis | Exploratory pipeline, PCA, QC plots | Verified on synthetic fixture |
| Analysis | Two-group log2-FPKM comparison with batch guard | Verified (matches SciPy t test) |
| Analysis | Count-based DE guards / estimability | Verified (unit tests); PyDESeq2 model call **Written** |
| Analysis | Real-data analysis of GSE128981 expression | **Partial**: expression file not provided |
| Experiments | Power, randomization, spec, Welch, BH | Verified (existing unit tests executed) |
| Networks | Graph builder, loaders, descriptive analysis, DE overlay | Verified (synthetic); real STRING/BioGRID files untested |
| ML | Train/evaluate/save/load/predict, report, CLI | Verified on synthetic data only |
| ML | Pathogen-risk model | **Future**: needs outcome labels |
| Economics | Break-even, sensitivity, Monte Carlo + EVPI | Verified (analytic checks) |
| Database | Models, repositories, Alembic 0001-0002 | Written (SQLAlchemy/Alembic not installed in sandbox) |
| API | All FastAPI routes incl. new ML/analysis/network/economics | Written; service logic Verified, HTTP layer not |
| Workflow | Nextflow ML workflow | Written, **not executed** (Nextflow absent) |
| CI | GitHub Actions (ruff, pytest, mkdocs) | Written, not run |
| Docs | MkDocs build | Verified (`mkdocs build`) |
| QA | pytest suite | Stand-in runner: 82 pass; API/DB tests unrunnable there; run `pytest` locally |
| QA | ruff, mypy, coverage | Not run (tools unavailable) |
