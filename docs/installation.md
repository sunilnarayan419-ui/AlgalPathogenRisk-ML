# Installation

## Windows PowerShell
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env        # optional; defaults work
```
## Linux / macOS
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```
Optional extras: `.[de]` (PyDESeq2), `.[postgres]`.

## Data
Place `GSE128981_series_matrix.txt.gz` (and, when you have it, `GSE128981_FPKMs.replicates.v2.tsv.gz`) in `data/raw/`,
or run `python scripts/download_geo.py` (needs network). See [Data analysis](data_analysis.md).

## Check the install
```powershell
pytest                                   # full suite
ruff check app tests scripts
mkdocs build --strict                    # or: mkdocs serve
python scripts\train_model.py --demo     # synthetic ML demo
uvicorn app.main:app --reload            # http://127.0.0.1:8000/docs
```

## Configuration (environment variables; all optional)
| Variable | Default | Meaning |
|---|---|---|
| `ALGAL_ENV` | `development` | `development`, `production` or `test` |
| `ALGAL_DATABASE_URL` | `sqlite:///./algal.db` | SQLite or PostgreSQL URL |
| `ALGAL_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `ALGAL_MODEL_DIR` | `models/current` | model artifact directory |

## Troubleshooting
- `ModuleNotFoundError: app` when running a script: run from the repo root (scripts add the root to `sys.path`).
- `FPKM validation failed: non-numeric...`: the file has an annotation column; use `--drop-columns <name>`.
- `/ready` shows `model_artifact.loaded: false`: run `POST /api/v1/models/train-demo` or `scripts/train_model.py`.
- Model load error mentioning scikit-learn version: retrain with the installed version.
- Database already created by the API, now using Alembic: `alembic stamp 0001` then `alembic upgrade head`.
