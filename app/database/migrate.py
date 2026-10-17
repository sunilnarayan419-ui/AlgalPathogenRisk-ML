"""Programmatic Alembic access (used by scripts/db_upgrade.py and tests).

Alembic files live at the repository root (alembic.ini, migrations/), next to the package,
so they are available from a source checkout / editable install and the Docker image
(which copies them). They are not shipped inside a built wheel.
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]


def make_config(url: str | None = None, connection=None) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    if url:
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    if connection is not None:
        cfg.attributes["connection"] = connection
    return cfg


def upgrade(url: str | None = None, revision: str = "head", connection=None) -> None:
    command.upgrade(make_config(url, connection), revision)


def downgrade(url: str | None = None, revision: str = "base", connection=None) -> None:
    command.downgrade(make_config(url, connection), revision)


def show_current(url: str | None = None) -> None:
    """Print current revision (CLI convenience)."""
    command.current(make_config(url))
