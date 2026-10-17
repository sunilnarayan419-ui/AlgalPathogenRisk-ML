# Roadmap

Done in code but **not yet executed by the authors** (run the tests, then treat as working): Alembic migrations, mypy configuration, lockfile tooling, STRING/BioGRID loaders, count-based DE with batch guards.

- **Raw reads -> counts**: a tested Nextflow/nf-core workflow for SRP189733 (see `count_based_de.md`). `workflows/nextflow/` still only wraps the audit + exploratory scripts and is untested.
- Generate and commit lockfiles (`scripts/lock_dependencies.ps1`), then install CI from them.
- Make `mypy` stricter (`check_untyped_defs`, then `disallow_untyped_defs`) once the first run is clean.
- Network analysis: enrichment with a proper background, network-aware features (only after labels exist).
- Outcome-labelled infection/stress experiments (see experiment design) -> validated vulnerability model with external validation and calibration.
- Expected-loss / decision-analysis references for the economics module.
