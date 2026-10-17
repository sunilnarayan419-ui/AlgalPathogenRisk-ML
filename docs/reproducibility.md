# Reproducibility

Seeds are explicit (splits, CV, PCA, randomization, permutation tests, Monte Carlo). Artifacts record seed, config,
data hash and software versions; datasets are keyed by SHA-256. Dependencies use bounded ranges in `pyproject.toml`
(generate hash-pinned lockfiles with `scripts/lock_dependencies.ps1`, then commit). CI uses synthetic fixtures, never
the full GEO file.

## Core demonstration (no external services)
```powershell
python scripts\train_model.py --demo --out models\current --report reports\model_report.json
python scripts\make_model_report.py --artifact-dir models\current --out reports\model_report.md
python scripts\make_synthetic_fixture.py
python scripts\run_analysis.py --fpkm tests\fixtures\SYNTHETIC_fpkm_gse128981_layout.tsv `
    --metadata data\metadata\sample_metadata_gsm.csv --out reports\exploratory --contrast UVM4 Elow47 --batch-col batch
uvicorn app.main:app --reload
```
## Nextflow (optional, untested)
```
nextflow run workflows/nextflow/main.nf --demo true --outdir results
```
The workflow wraps `scripts/train_model.py` only. Nextflow was not available, so it was neither executed nor
syntax-checked; run `nextflow run ... -stub-run` or a real run before relying on it.
