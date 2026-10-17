# Database and migrations

Tables: `datasets`, `dataset_versions` (SHA-256), `data_audits`, `analysis_runs`, `model_evaluations`, `experiments`,
`economic_scenarios`, `reference_records`, **`model_versions`** (artifact path, checksum, feature schema, metrics,
synthetic/calibrated flags) and **`network_records`** (sources, node/edge counts, file path and checksum). Matrices,
models and graphs stay on disk. SQLite is the local default; PostgreSQL via `ALGAL_DATABASE_URL`.

Repository functions (`app/database/repositories.py`): dataset/version/audit registration (idempotent on checksum),
analysis runs, model evaluations, model-version registration (idempotent on model checksum), network registration
(duplicate names rejected), scenario and experiment saving.

```powershell
alembic upgrade head                       # or: python scripts\db_upgrade.py
alembic current
alembic revision --autogenerate -m "describe the change"   # then REVIEW the file
alembic downgrade -1
```
Revisions: `0001` initial schema, `0002` model_versions + network_records. `ALGAL_DATABASE_URL` selects the DB,
so no credentials live in `alembic.ini`. If the API already created the tables via `create_all`, run `alembic stamp 0001`
then `alembic upgrade head`.

**Status: written, not executed** (SQLAlchemy and Alembic were unavailable in the authoring sandbox).
`tests/integration/test_migrations.py` checks that migrations reproduce the ORM schema; run it locally with `pytest`.
