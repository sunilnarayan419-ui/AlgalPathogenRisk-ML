# Limitations

- GSE128981 is an observational strain comparison about transgene silencing (SRTA, a sirtuin-type histone deacetylase). It has no infection, stress-collapse or production-failure labels. Genotype classification is **not** culture-risk prediction (`app/ml/baseline.py::RISK_MODEL_STATUS`).
- The supplied series-matrix file has an **empty expression table**. No analysis of real expression values was performed. The FPKM file has not been inspected; its column names and annotation columns are unknown.
- Every ML, DE-overlay and network result in this repository comes from **synthetic data** and shows software behaviour only. Held-out metrics from tiny synthetic splits (30 rows) are noisy; no confidence intervals are reported for them.
- Replicates of one strain are not independent of strain identity: cross-validation estimates recognition of *seen* strains, not generalisation to new ones.
- FPKM is not a count. The log2-FPKM comparison is exploratory (equal variances, independent replicates assumed). Count-based DE needs raw counts that this repository does not contain; the PyDESeq2 model call has never run.
- Batch for GSE128981 is inferred from accession blocks and design text and is confounded with genotype (WT vs complemented lines share no batch).
- ML scores are uncalibrated; no external validation exists; thresholds are chosen by max-F1 on a small validation split.
- STRING/BioGRID loaders follow documented file formats but were run only on synthetic files. Gene-identifier mismatch with the expression matrix is likely until checked (`expression_overlap`).
- Economic outputs use hypothetical inputs and uniform assumption ranges only.
- Not executed in the authoring sandbox (no FastAPI/SQLAlchemy/Alembic/pytest/Nextflow/network): HTTP routes, SQL repositories, Alembic migrations 0001-0002, Nextflow workflow, GitHub Actions, download scripts, ruff, mypy.
- No dependency lockfile is committed: generate it with `scripts/lock_dependencies.ps1`.
