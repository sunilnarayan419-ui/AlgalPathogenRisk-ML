# Database migrations (Alembic)

Schema changes are versioned in `migrations/versions/`; revision `0001` mirrors
`app/database/models.py` at v0.1.0. `ALGAL_DATABASE_URL` (the same variable as the API) selects the
database, so no credentials are stored in `alembic.ini`.

```powershell
alembic upgrade head                       # or: python scripts\db_upgrade.py
alembic current
alembic revision --autogenerate -m "describe the change"   # then REVIEW the generated file
alembic downgrade -1
python scripts\db_upgrade.py --url postgresql+psycopg2://user:pw@localhost:5432/algal
```

* Already have a database created by the API's `create_all` (no `alembic_version` table)? Run
  `alembic stamp 0001` once instead of `upgrade`.
* The Docker image runs `alembic upgrade head` before starting the API.
* `tests/integration/test_migrations.py` checks that the migrations reproduce the ORM schema on SQLite,
  and (when `ALGAL_DATABASE_URL` is PostgreSQL) on PostgreSQL; CI has a PostgreSQL job for this.
* Not covered: data migrations, zero-downtime changes, SQLite `ALTER` limitations beyond batch mode.

**Status:** written, not executed.
