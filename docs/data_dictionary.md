# Data dictionary

| Item | Meaning |
|---|---|
| FPKM matrix | genes (rows) x samples (columns), FPKM — normalized abundance, not counts (assumed orientation; confirm) |
| `log2_fpkm.csv` | log2(FPKM+1), derived copy |
| metadata CSV | `sample_id`, `group` (required); `batch` (optional). Unresolved annotations stay blank, never invented |
| SQL tables | datasets, dataset_versions (sha256), data_audits, analysis_runs, model_evaluations, experiments, economic_scenarios, reference_records, model_versions, network_records |

## GSE128981 sample structure (from the official series-matrix metadata)

21 samples, platform GPL26362 (Illumina HiSeq 4000), polyA RNA, liquid mid-log photo-heterotrophic cultures, no treatment. Expression = Cuffdiff FPKM, STAR alignment, genome v5.5.

| Strain | Genotype | n | Batch (inferred) |
|---|---|---|---|
| Elow47 | SRTA WT | 4 | 1 |
| UVM4 | srta mutant | 4 | 1 |
| UVM11 | srta mutant | 7 (reps 1-4 batch 1, reps 5-7 batch 2) | 1 and 2 |
| UVM11-C1 | SRTA complemented | 3 | 2 |
| UVM11-C9 | SRTA complemented | 3 | 2 |

Batch is **not** a per-sample field in GEO. It is inferred from the series' overall-design text (two batches; UVM11 repeated in batch 2 "to identify batch effects") and the two GSM accession blocks (GSM3689501-512, GSM4733487-495). Generated files: `data/metadata/sample_manifest.csv`, `sample_metadata_gsm.csv`, `sample_metadata_title.csv`.


## Parsed GEO sample table (`app/data/geo.py`)
`sample_accession`, `title`, one `char_<key>` column per `!Sample_characteristics_ch1` entry (e.g. `char_strain`, `char_genotype`),
and every other `!Sample_*` field lower-cased without the prefix (repeated fields get `_2`, `_3`...).

## ML artifact (`models/current/`)
| File | Content |
|---|---|
| `model.joblib` | fitted sklearn Pipeline (preprocessing + classifier) |
| `metadata.json` | format version, feature list/schema, threshold, seed/config, data hash, provenance, test metrics, caveats, `synthetic`, `calibrated`, model SHA-256, software versions |
| `evaluation_report.json` | candidates, validation/test metrics, dummy baseline, calibration table, error analysis, leakage controls |

## Training table contract
Numeric feature columns, binary 0/1 target (default `label`), group id column (default `group`) identifying
independent units; replicates share a group id.
