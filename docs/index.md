# AlgalPathogenRisk-ML / Algae Culture Vulnerability Prototype

Research prototype for *Chlamydomonas reinhardtii* transcriptomics: data ingestion and QC, exploratory
statistics, provenance-tagged networks, a leakage-safe machine-learning pipeline, a FastAPI backend, SQL
provenance storage and hypothetical economic decision support.

**Read first:** [Scientific scope](scientific_scope.md) and [Implementation status](implementation_status.md).
The only supplied real dataset (GEO GSE128981) has no infection or culture-collapse labels, so **no
pathogen-risk prediction is claimed**. ML code is demonstrated on clearly labelled synthetic data.
