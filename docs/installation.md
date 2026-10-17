# Installation (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
python scripts\download_geo.py                      # needs network; skip if you already have the file
python scripts\audit_dataset.py --input data\raw\GSE128981_FPKMs.replicates.v2.tsv.gz
python scripts\run_analysis.py --input data\raw\GSE128981_FPKMs.replicates.v2.tsv.gz
pytest --cov=app; ruff check .; mkdocs build --strict
uvicorn app.main:app --reload                       # http://127.0.0.1:8000/docs
```

If the audit reports a non-numeric column (e.g. gene annotation), re-run with `--drop-columns <name>`; the real header has not been inspected by the authors. Metadata for grouping: CSV with `sample_id,group[,batch]` built from the GEO sample manifest; groups are never guessed.

## Added tooling

```powershell
pip install -e ".[dev,de]"          # de = PyDESeq2 for count-based DE; add postgres for PostgreSQL
alembic upgrade head                # create/upgrade the database schema
mypy                                # type check (lenient config)
.\scripts\lock_dependencies.ps1     # generate requirements.lock / requirements-dev.lock, then commit them
python scripts\download_interactions.py --taxon 3055
python scripts\build_network.py --string <file> --string-version v12.0 --expression <fpkm.tsv.gz>
python scripts\run_count_de.py --counts <raw_counts.tsv> --metadata data\metadata\sample_manifest.csv --group-col strain --batch-col batch --list-estimable
```
Note: `SQLAlchemy` and `alembic` are now declared dependencies (SQLAlchemy was imported but previously not listed in `pyproject.toml`).
