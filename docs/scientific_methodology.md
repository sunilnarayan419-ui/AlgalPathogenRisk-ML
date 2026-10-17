# Scientific methodology

1. **Retrieve & verify** (`scripts/download_geo.py`): fixed NCBI URLs, gzip integrity check, SHA-256 manifest.
2. **Parse** (`app/data/geo.py`): streaming GEO series-matrix parser (plain/gz, quoted TSV, begin/end markers;
   truncated files and misaligned columns are errors; empty tables are reported, not filled).
3. **Audit** (`scripts/audit_dataset.py`): samples, groups, alignment, missing/duplicate ids, negative values,
   robust outlier flags, measurement-type heuristic (counts-like vs normalised vs log), suitability statement.
4. **Load expression** (`app/data/loader.py`): strict FPKM loader (ids, duplicates, NaN/inf/negatives, numeric).
5. **Explore** (`app/analysis/pipeline.py`): `log2(FPKM+1)` stored separately; per-sample distributions;
   correlations; PCA coloured by provided groups and by inferred batch.
6. **Compare groups** (`app/analysis/de_fpkm.py`): per-gene OLS on log2(FPKM+1) with optional batch term, t test
   on the group coefficient (equals Student's t test with one batch), BH FDR, difference with CI, Hedges' g.
   Contrasts that cannot be separated from batch are refused (`ConfoundingError`, CLI exit 3) unless explicitly
   overridden, in which case results are flagged `batch_confounded`. This is **not** negative-binomial DE.
7. **Count-based DE** (`app/experiments/count_de.py`, optional PyDESeq2): only for raw integer counts.
8. **Networks** (`app/networks/`): provenance-tagged graphs; descriptive metrics; DE overlay with seeded
   permutation test of edge density among significant genes. Descriptive, not causal.
9. **ML** (`app/ml/pipeline.py`): see [Model validation](model_validation.md).
10. **Economics** (`app/services/economics_core.py`): see [Economic decision support](economic_decision_support.md).

Assumptions to check: independent biological replicates; equal variances for the OLS model; pseudocount 1
damps fold changes of low-expressed genes; GSE128981 batch labels are inferred (see [data dictionary](data_dictionary.md)).
