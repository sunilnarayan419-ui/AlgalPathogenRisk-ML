# Reproducibility

Seeds are explicit (randomization, PCA, CV). Runs record software versions; datasets are keyed by SHA-256. Dependencies use bounded ranges in `pyproject.toml` (hash-pinned lockfiles are generated locally with `scripts/lock_dependencies.ps1` / `make lock`, then committed). CI uses synthetic fixtures, never the full GEO file. SQL: SQLite locally; set `ALGAL_DATABASE_URL` to PostgreSQL for deployment (schema is created idempotently; use `alembic upgrade head`, see `database_migrations.md`).
