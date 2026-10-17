# Architecture

```
app/data         strict FPKM + raw-count loaders         app/services   original prototype services
app/analysis     log2, QC, PCA, pipeline                  app/experiments design, power, randomization, analysis
app/ml           grouped baseline + risk-model status     app/networks    provenance-tagged graph + STRING/BioGRID loaders
app/database     SQLAlchemy models/repositories/migrate; migrations/ = Alembic          app/routes      versioned FastAPI routers (/api/v1)
```
Science code never imports FastAPI. Large matrices stay on disk; SQL stores checksums, audits, runs, plans, scenarios. Design decision: the repository's `app/` layout was kept rather than moved to `src/`.
