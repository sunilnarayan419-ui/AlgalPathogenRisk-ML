# Model validation

Only a genotype/strain-group baseline is offered. Scaling is inside each training fold; grouped CV (`StratifiedGroupKFold`) keeps related samples together; ungrouped CV is refused unless explicitly allowed. With too few samples/groups the function returns `insufficient_data` and **no metrics**.

Replicates of one strain cannot be held out as groups for a strain label (classes would vanish from training), so reported scores measure recognition of *seen* strains — exploratory, not external validation. The culture-vulnerability model is reported `available: false` until outcome-labelled data exist.

## What the real design allows (GSE128981)

- **Genotype is confounded with batch**: all WT (Elow47) samples are in batch 1 and all complemented samples in batch 2. A WT-vs-complemented classifier can learn batch instead of biology.
- UVM11 is the only strain in both batches (4 + 3 samples): use it to quantify batch effect (e.g. PCA by batch, `pca_by_batch.png`).
- A less confounded exploratory task is WT vs srta-mutant **within batch 1** (4 vs 8 samples). With so few samples any score is exploratory; the strain-level label cannot be held out by strain.


## Tabular classifier pipeline (`app/ml/pipeline.py`)

Status: **implemented; verified in a restricted sandbox only for the pure-Python/scikit-learn parts**
(see `docs/testing.md`). It is generic software. It is **not** trained on GSE128981 and produces no
pathogen-risk claim.

- **Target**: binary 0/1 column supplied by the caller. Single-class, non-binary, missing-label
  and too-rare-class targets are rejected.
- **Splits**: `GroupShuffleSplit` into train/validation/test; samples sharing a group id (replicates)
  never cross splits. Cross-validation on the training part uses `StratifiedGroupKFold`.
- **Leakage controls**: imputation and scaling are inside the sklearn `Pipeline`; the model is chosen
  and the threshold (max F1) is set on validation data; the test set is scored once.
- **Candidates**: `DummyClassifier` (prior), L2 logistic regression, random forest,
  `HistGradientBoostingClassifier`. The dummy baseline is always reported next to the selected model.
- **Metrics**: ROC-AUC, average precision, precision, sensitivity, specificity, F1, Brier score,
  confusion matrix, quantile-bin calibration table. Undefined metrics are `null`, never 0.
- **Artifact** (`models/current/`): `model.joblib`, `metadata.json` (feature schema, threshold, seed,
  config, data hash, software versions, SHA-256 of the model file), `evaluation_report.json`.
  Loading checks format version, checksum and scikit-learn major version.
- **Prediction**: record keys must equal the training features exactly; non-numeric and infinite values
  are rejected. Output states `calibrated: false` and whether training data were synthetic.

### What real risk prediction would need

Outcome labels (infection, collapse, production failure) on independent cultures with a defined
horizon, batch/group-aware validation, external validation, then calibration on held-out data.

### Synthetic demonstration

`python scripts/train_model.py --demo` trains on generated data. In one verified run the held-out
test set had only 30 rows (AUC 0.71, specificity 0.30); with that size these numbers are very noisy
and describe synthetic data only.


## Error analysis and report
`scripts/make_model_report.py` renders `evaluation_report.json` into Markdown (dataset, methodology, candidate table, test metrics beside the
dummy baseline, confusion matrix, false-positive/negative units, calibration bins, limitations, reproduction command). Reports for synthetic
runs carry a SYNTHETIC banner. Pathogen-risk labels, external validation and calibration remain **future work**.
