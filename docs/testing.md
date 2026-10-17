# Testing

`pytest --cov=app`. Unit: power, randomization, spec, analysis, economics, loader, pipeline, network, ML. API and DB integration tests use in-memory SQLite. All test data is synthetic and labelled so.

Also: `ruff check .`, `mypy`, `mkdocs build --strict`. Added tests: `tests/unit/test_network_loaders.py` (STRING/BioGRID, synthetic fixtures), `tests/unit/test_counts_loader.py`, `tests/unit/test_count_de.py` (guardrails run anywhere; the PyDESeq2 model test is skipped unless `pydeseq2` is installed; one test reads the real sample manifest) and `tests/integration/test_migrations.py` (SQLite always, PostgreSQL when `ALGAL_DATABASE_URL` points to one). None of these had been executed when they were written.
