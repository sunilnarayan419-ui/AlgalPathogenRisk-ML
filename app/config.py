"""Environment-driven settings with validation (no secrets in source)."""
from __future__ import annotations

import os
from dataclasses import dataclass

ENVS = {"development", "production", "test"}


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    log_level: str


def get_settings() -> Settings:
    env = os.environ.get("ALGAL_ENV", "development")
    if env not in ENVS:
        raise ValueError(f"ALGAL_ENV must be one of {sorted(ENVS)}, got {env!r}.")
    url = os.environ.get("ALGAL_DATABASE_URL", "sqlite:///./algal.db")
    if not url.startswith(("sqlite://", "postgresql://", "postgresql+psycopg2://")):
        raise ValueError("ALGAL_DATABASE_URL must be a sqlite:// or postgresql:// URL.")
    level = os.environ.get("ALGAL_LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ValueError("ALGAL_LOG_LEVEL must be DEBUG/INFO/WARNING/ERROR.")
    return Settings(env=env, database_url=url, log_level=level)
