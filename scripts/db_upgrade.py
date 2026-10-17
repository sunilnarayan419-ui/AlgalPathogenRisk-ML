"""Apply Alembic migrations: python scripts/db_upgrade.py [--url sqlite:///./algal.db] [--revision head]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402
from app.database import migrate  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--url", default=None)
ap.add_argument("--revision", default="head")
a = ap.parse_args()
migrate.upgrade(a.url or get_settings().database_url, a.revision)
print("migrated to", a.revision)
