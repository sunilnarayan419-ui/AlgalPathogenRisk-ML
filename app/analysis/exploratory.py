"""Transparent exploratory transcriptomics on a genes x samples FPKM table.

FPKM is a normalized abundance, NOT a count: nothing here is count-based differential
expression. Original values are never modified; transforms return new frames.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def log2_fpkm(fpkm: pd.DataFrame, pseudocount: float = 1.0) -> tuple[pd.DataFrame, dict]:
    if (fpkm < 0).any().any():
        raise ValueError("Negative FPKM values; run validation first.")
    return np.log2(fpkm + pseudocount), {"transform": "log2(FPKM + c)", "pseudocount": pseudocount}


def sample_correlations(logged: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    return logged.corr(method=method)


def pca_scores(logged: pd.DataFrame, n_components: int = 2, top_variable_genes: int | None = 500,
               seed: int = 0) -> dict:
    """PCA of samples (centered, unscaled log values), optionally on the most variable genes."""
    from sklearn.decomposition import PCA
    x = logged.loc[logged.var(axis=1) > 0]
    if top_variable_genes and len(x) > top_variable_genes:
        x = x.loc[x.var(axis=1).nlargest(top_variable_genes).index]
    n_components = min(n_components, x.shape[1], x.shape[0])
    pca = PCA(n_components=n_components, random_state=seed)
    scores = pca.fit_transform(x.T.to_numpy())
    cols = [f"PC{i + 1}" for i in range(n_components)]
    return {"scores": pd.DataFrame(scores, index=x.columns, columns=cols),
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "n_genes_used": int(len(x))}


def qc_summary(fpkm: pd.DataFrame, min_fpkm: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame({
        "total_fpkm": fpkm.sum(),
        "genes_detected_fpkm_ge_min": (fpkm >= min_fpkm).sum(),
        "zero_fraction": (fpkm == 0).mean(),
        "median_fpkm": fpkm.median()})


def plot_pca(pca: dict, groups: pd.Series, path: str | Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = pca["scores"]
    fig, ax = plt.subplots(figsize=(6, 5))
    for g in sorted(groups.unique()):
        idx = groups[groups == g].index.intersection(s.index)
        ax.scatter(s.loc[idx, "PC1"], s.loc[idx, "PC2"], label=str(g))
    evr = pca["explained_variance_ratio"]
    ax.set_xlabel(f"PC1 ({evr[0]:.1%} variance)")
    ax.set_ylabel(f"PC2 ({evr[1]:.1%} variance)" if len(evr) > 1 else "PC2")
    ax.set_title("PCA of log2(FPKM+1), samples")
    ax.legend(title="Group")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
