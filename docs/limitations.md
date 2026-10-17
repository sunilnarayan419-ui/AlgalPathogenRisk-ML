# Limitations

- GSE128981 is observational strain comparison data: no infection, stress-collapse or production-failure labels. Genotype classification is **not** culture-risk prediction (`app/ml/baseline.py::RISK_MODEL_STATUS`).
- Replicates of one strain are not independent of strain identity: cross-validation estimates recognition of *seen* strains, not generalisation to new ones.
- FPKM is not a count. Count-based DE code exists (`count_de.py`) but has never run and needs raw counts that this repository does not contain.
- Economic outputs use hypothetical inputs only.
- The Nextflow workflow only wraps the audit/exploratory scripts and is untested; no FASTQ processing exists. API, SQL and API tests were written but could not be executed in the authoring sandbox.
- Batch assignment for GSE128981 is inferred (see data dictionary) and confounded with genotype.
- The FPKM file itself has still not been inspected by the authors; sample column names are unknown.
- STRING/BioGRID loaders were written against documented file formats, not against the real files; the STRING download URL and BioGRID TAB3 column names are unverified. Gene-identifier mismatch with the expression matrix is likely until checked.
- Alembic migration `0001` was hand-written to mirror the models and has not been applied to a database by the authors.
- mypy is configured leniently and has not been run; expect a first batch of type errors.
- No dependency lockfile is committed: generate it with `scripts/lock_dependencies.ps1`.
