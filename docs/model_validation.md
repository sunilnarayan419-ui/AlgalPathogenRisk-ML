# Model validation

Only a genotype/strain-group baseline is offered. Scaling is inside each training fold; grouped CV (`StratifiedGroupKFold`) keeps related samples together; ungrouped CV is refused unless explicitly allowed. With too few samples/groups the function returns `insufficient_data` and **no metrics**.

Replicates of one strain cannot be held out as groups for a strain label (classes would vanish from training), so reported scores measure recognition of *seen* strains — exploratory, not external validation. The culture-vulnerability model is reported `available: false` until outcome-labelled data exist.

## What the real design allows (GSE128981)

- **Genotype is confounded with batch**: all WT (Elow47) samples are in batch 1 and all complemented samples in batch 2. A WT-vs-complemented classifier can learn batch instead of biology.
- UVM11 is the only strain in both batches (4 + 3 samples): use it to quantify batch effect (e.g. PCA by batch, `pca_by_batch.png`).
- A less confounded exploratory task is WT vs srta-mutant **within batch 1** (4 vs 8 samples). With so few samples any score is exploratory; the strain-level label cannot be held out by strain.
