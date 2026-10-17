"""End-to-end exploratory run: validate -> QC -> log2 -> correlations -> PCA -> reports."""
from __future__ import annotations

import datetime as dt
import json
import platform
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import scipy
import sklearn

from app.analysis import exploratory as ex
from app.data.loader import load_fpkm

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def run_exploratory(fpkm_path, out_dir, metadata_csv=None, seed: int = 42,
                    expected_samples: int | None = None, **loader_kwargs) -> dict:
    """metadata_csv (optional) needs columns sample_id,group[,batch]. Groups are never inferred."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fpkm, report = load_fpkm(fpkm_path, expected_samples=expected_samples, **loader_kwargs)
    groups = None
    batches = None
    if metadata_csv:
        meta = pd.read_csv(metadata_csv)
        missing = {"sample_id", "group"} - set(meta.columns)
        if missing:
            raise ValueError(f"metadata missing columns {sorted(missing)}")
        if meta["sample_id"].duplicated().any():
            raise ValueError("duplicate sample_id in metadata")
        unmatched = set(fpkm.columns) ^ set(meta["sample_id"])
        if unmatched:
            raise ValueError(f"samples differ between matrix and metadata: {sorted(unmatched)[:5]}")
        groups = meta.set_index("sample_id")["group"].reindex(fpkm.columns)
        if "batch" in meta.columns and (meta["batch"] != "unresolved").any():
            batches = meta.set_index("sample_id")["batch"].reindex(fpkm.columns)

    logged, transform = ex.log2_fpkm(fpkm)
    qc = ex.qc_summary(fpkm)
    corr = ex.sample_correlations(logged)
    pca = ex.pca_scores(logged, seed=seed)
    qc.to_csv(out / "qc_summary.csv")
    corr.to_csv(out / "sample_correlations.csv")
    pca["scores"].to_csv(out / "pca_scores.csv")
    logged.to_csv(out / "log2_fpkm.csv")  # transformed copy; raw FPKM untouched

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot([logged[c] for c in logged.columns])
    ax.set_xticklabels(list(logged.columns))
    ax.set_xlabel("Sample")
    ax.set_ylabel("log2(FPKM + 1)")
    ax.set_title("Expression distribution per sample")
    plt.setp(ax.get_xticklabels(), rotation=90)
    fig.savefig(out / "distributions.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    ex.plot_pca(pca, groups if groups is not None else pd.Series("unlabelled", index=fpkm.columns),
                out / "pca.png")

    if batches is not None:  # same PCA coloured by batch: strong batch structure = confounding risk
        ex.plot_pca(pca, batches, out / "pca_by_batch.png")

    summary = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "seed": seed,
               "input": report, "transform": transform,
               "pca_explained_variance_ratio": pca["explained_variance_ratio"],
               "pca_genes_used": pca["n_genes_used"],
               "min_sample_correlation": float(np.nanmin(corr.to_numpy())),
               "groups_provided": groups is not None,
               "software": {"python": platform.python_version(), "pandas": pd.__version__,
                            "numpy": np.__version__, "scipy": scipy.__version__,
                            "sklearn": sklearn.__version__},
               "interpretation_limits": [
                   "Exploratory only; FPKM is not counts, so no count-based DE is run.",
                   "PCA separation does not establish infection or collapse risk."]}
    (out / "exploratory_report.json").write_text(json.dumps(summary, indent=2) + "\n")
    md = ["# Exploratory transcriptomic report", "",
          f"- File: `{report['path']}` (sha256 `{report['sha256']}`)",
          f"- Genes x samples: {report['n_genes']} x {report['n_samples']}",
          f"- Transform: {transform['transform']} (c={transform['pseudocount']})",
          f"- PC1/PC2 variance: {pca['explained_variance_ratio'][:2]}",
          f"- Lowest pairwise sample correlation: {summary['min_sample_correlation']:.3f}",
          f"- Groups provided: {groups is not None}", "",
          "**Limits:** " + " ".join(summary["interpretation_limits"])]
    (out / "exploratory_report.md").write_text("\n".join(md) + "\n")
    return summary
