"""Alembic migrations must reproduce the ORM schema exactly (SQLite always; PostgreSQL in CI)."""
import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.database import migrate
from app.database.connection import init_db, make_engine
from app.database.models import Base


def _diffs(engine):
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": False})
        return compare_metadata(ctx, Base.metadata)


def test_sqlite_upgrade_matches_models_and_downgrades(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    migrate.upgrade(url)
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables and "alembic_version" in tables
    assert _diffs(engine) == []
    init_db(make_engine(url))            # create_all after migrating is a no-op, not an error
    migrate.downgrade(url, "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}


def test_upgrade_is_repeatable(tmp_path):
    url = f"sqlite:///{(tmp_path / 'r.db').as_posix()}"
    migrate.upgrade(url)
    migrate.upgrade(url)                 # already at head: no error


@pytest.mark.skipif(not os.environ.get("ALGAL_DATABASE_URL", "").startswith("postgresql"),
                    reason="needs ALGAL_DATABASE_URL pointing to a migrated PostgreSQL database")
def test_postgres_migration_matches_models():
    engine = create_engine(os.environ["ALGAL_DATABASE_URL"])
    assert _diffs(engine) == []
