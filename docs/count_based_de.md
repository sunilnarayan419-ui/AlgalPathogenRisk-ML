# Count-based differential expression

**Status:** the guard logic (counts validation, size factors, estimability) is covered by unit tests that were executed; the PyDESeq2 model call and `scripts/run_count_de.py` end-to-end have not been run. No raw count matrix for GSE128981 exists in this repository, and no raw count matrix for
GSE128981 exists in this repository. The GEO supplementary file is FPKM, which is **not** valid input.

## Getting raw counts (not implemented here)

Options, cheapest first:

1. Check the GEO record (`GSE128981`) and the associated paper for a raw-count supplement.
2. Process the reads from SRA project SRP189733 yourself, for example with the nf-core pipelines
   [`fetchngs`](https://nf-co.re/fetchngs) (downloads FASTQ and writes a samplesheet) followed by
   [`rnaseq`](https://nf-co.re/rnaseq) (alignment/quantification, writes a merged gene-count table). You
   need a *C. reinhardtii* genome and annotation whose gene IDs match the identifiers you will use
   downstream. These commands have not been tested for this project; read the pipeline docs for
   current parameters.
3. Use Salmon/RSEM estimated counts: pass `--round-noninteger`; the rounding is recorded.

The count columns will usually be run IDs (SRR...); map them to the manifest's GSM accessions with
`--sample-map map.csv` (columns `column_name,sample_id`).

## Workflow

```powershell
pip install -e ".[de]"      # installs PyDESeq2
# 1. which contrasts can be separated from batch?
python scripts\run_count_de.py --counts data\raw\gene_counts.tsv --metadata data\metadata\sample_manifest.csv `
    --group-col strain --batch-col batch --list-estimable
# 2. one comparison
python scripts\run_count_de.py --counts data\raw\gene_counts.tsv --metadata data\metadata\sample_manifest.csv `
    --group-col strain --batch-col batch --group-a UVM11 --group-b Elow47
```

Outputs (`reports/count_de/`): `estimable_contrasts.csv`, `de_<a>_vs_<b>.csv`, `de_<a>_vs_<b>.json`.
Exit codes: 0 ok, 1 invalid input, 2 usage, 3 refused by a design guard.

## Guardrails

* Raw non-negative integer counts only; normalised or non-integer data is rejected.
* Sample IDs must match between counts and metadata in both directions; groups are never inferred.
* At least `min_replicates` (default 2) samples per compared group.
* **Batch estimability**: a contrast must lie in the row space of the design matrix. If the two groups
  share no batch and nothing bridges them, `ConfoundingError` is raised (override with
  `--allow-unadjusted`, which marks the result `batch_confounded`).
* If groups can be separated only through *other* strains that occur in both batches (the situation for
  WT vs complemented samples in GSE128981 via UVM11), the result is flagged
  `bridged_through_other_groups_assumes_additive_batch_effect`; that needs `--use-all-samples` and
  assumes the batch shift is the same for every strain. Batch is *inferred* for this dataset (see the
  data dictionary).
* Low-count genes are filtered (default: >= 10 counts in >= 3 samples).

## Interpreting results

Differences between strains are observational. They say nothing about infection or culture-collapse
risk, and with 3-4 replicates per strain and partly inferred batches, hits are hypotheses. The within-batch
comparisons (batch 1: Elow47, UVM4, UVM11 reps 1-4; batch 2: UVM11 reps 5-7 and complemented lines) are the
cleanest.

## Known limits

PyDESeq2's keyword arguments changed between releases; `run_deseq2` tries `design="~..."` and falls back
to `design_factors=[...]` but has not been checked against an installed version. Not implemented: LFC
shrinkage, interaction designs, within-batch random effects, gene-set enrichment.
