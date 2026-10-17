# Scientific methodology

1. **Retrieve & verify** (`download_geo.py`): checksum, gzip integrity, no overwrite.
2. **Audit** (`app/data/loader.py`): ids, duplicates, NaN/inf/negative/non-numeric, sample count.
3. **Preprocess**: `log2(FPKM+1)` stored separately; raw FPKM untouched; the transform is recorded in the report.
4. **Explore**: sample distributions, correlations, PCA (centered log values; most variable genes), coloured by *provided* groups.
5. No count-based differential expression is applied to FPKM. Use raw counts (SRA SRP189733) for that, which is future work.

Refs: Conesa et al. 2016 (see references).
