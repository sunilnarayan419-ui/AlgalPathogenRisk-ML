"""Exploratory per-gene comparison of two groups on log2(FPKM + c), with BH correction.

FPKM is a normalised abundance, not a count, so this is NOT a negative-binomial analysis and
does not replace count-based DE (``app.experiments.count_de``). It is an ordinary-least-squares
model per gene: log2(FPKM+c) ~ group [+ batch], tested with a t statistic on the group term
(equal-variance assumption). With one batch and two groups it equals Student's t test.

Reported per gene: difference of mean log2 values (a - b) with CI, t, df, p, BH-adjusted p,
and Hedges' g. The "log2 fold change" is a difference on the log2(FPKM+c) scale and is damped
for low-expressed genes by the pseudocount.

Guards: >= min_replicates per group; sample ids must be unique; a contrast that cannot be
separated from batch raises ConfoundingError unless allow_unadjusted=True (then flagged).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from app.experiments.analysis import benjamini_hochberg
from app.experiments.count_de import (
    ConfoundingError,
    DesignError,
    contrast_estimable,
)

CAVEAT = ("Exploratory: OLS on log2(FPKM+c) assuming independent biological replicates and equal "
          "variances. Strain/genotype differences are observational and say nothing about "
          "infection or culture-collapse risk.")


def differential_expression_log2(fpkm: pd.DataFrame, meta: pd.DataFrame, group_col: str,
                                 group_a: str, group_b: str, batch_col: str | None = None,
                                 pseudocount: float = 1.0, min_fpkm: float = 1.0,
                                 min_detect_samples: int = 2, min_replicates: int = 2,
                                 allow_unadjusted: bool = False, confidence: float = 0.95
                                 ) -> tuple[pd.DataFrame, dict]:
    """fpkm: genes x samples; meta indexed by sample id (same ids as fpkm.columns)."""
    if fpkm.columns.has_duplicates or fpkm.index.has_duplicates:
        raise ValueError("duplicate sample or gene identifiers.")
    if not set(meta.index) >= set(fpkm.columns):
        raise ValueError("metadata lacks some matrix samples.")
    if (fpkm < 0).any().any() or not np.isfinite(fpkm.to_numpy(float)).all():
        raise ValueError("FPKM must be finite and non-negative.")
    meta = meta.loc[fpkm.columns]
    g_all = meta[group_col].astype(str)
    if group_a == group_b:
        raise ValueError("group_a and group_b must differ.")
    for lvl in (group_a, group_b):
        if lvl not in set(g_all):
            raise DesignError(f"group {lvl!r} not in metadata")
    sel = g_all.isin([group_a, group_b])
    m, x = meta[sel], fpkm.loc[:, sel.to_numpy()]
    g = m[group_col].astype(str)
    n_a, n_b = int((g == group_a).sum()), int((g == group_b).sum())
    if min(n_a, n_b) < min_replicates:
        raise DesignError(f"need >= {min_replicates} samples per group (have {n_a} and {n_b}).")

    flags: list[str] = []
    use_batch = batch_col is not None and m[batch_col].astype(str).nunique() > 1
    if use_batch and not contrast_estimable(m, group_col, group_a, group_b, batch_col):
        if allow_unadjusted:
            use_batch = False
            flags.append("batch_confounded")
        else:
            raise ConfoundingError(f"{group_a!r} vs {group_b!r} cannot be separated from "
                                   f"{batch_col!r} with these samples; compare within a batch or "
                                   "pass allow_unadjusted=True.")
    cols = [pd.Series(1.0, index=m.index), (g == group_a).astype(float)]
    if use_batch:
        b = m[batch_col].astype(str)
        cols += [(b == lvl).astype(float) for lvl in sorted(b.unique())[1:]]
    design = np.column_stack([c.to_numpy() for c in cols])
    n, p = design.shape
    if n - p < 1:
        raise DesignError("no residual degrees of freedom for this design.")

    detected = (x >= min_fpkm).sum(axis=1) >= min_detect_samples
    xk = x.loc[detected]
    if xk.shape[0] == 0:
        raise DesignError("no genes pass the detection filter.")
    y = np.log2(xk.to_numpy(float) + pseudocount).T          # samples x genes
    xtx_inv = np.linalg.pinv(design.T @ design)
    beta = xtx_inv @ design.T @ y
    resid = y - design @ beta
    df = n - p
    s2 = (resid ** 2).sum(axis=0) / df
    se = np.sqrt(s2 * xtx_inv[1, 1])
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta[1] / se, np.nan)
    pval = 2 * stats.t.sf(np.abs(t), df)
    tcrit = stats.t.ppf(1 - (1 - confidence) / 2, df)
    sp = np.sqrt(s2)
    with np.errstate(divide="ignore", invalid="ignore"):
        hedges = np.where(sp > 0, beta[1] / sp, np.nan) * (1 - 3 / (4 * df - 1))
    ok = np.isfinite(pval)
    padj = np.full(len(pval), np.nan)
    padj[ok] = benjamini_hochberg(pval[ok])
    res = pd.DataFrame({
        "log2_diff_a_minus_b": beta[1], "ci_low": beta[1] - tcrit * se,
        "ci_high": beta[1] + tcrit * se, "t": t, "df": df, "p_value": pval, "padj_bh": padj,
        "hedges_g": hedges, "mean_log2_a": y[(g == group_a).to_numpy()].mean(axis=0),
        "mean_log2_b": y[(g == group_b).to_numpy()].mean(axis=0)}, index=xk.index)
    res.index.name = "gene_id"
    res = res.sort_values("padj_bh", na_position="last")
    report = {"method": "OLS on log2(FPKM + c), t test on group term, BH FDR",
              "contrast": f"{group_a} vs {group_b} (a - b)", "n_a": n_a, "n_b": n_b,
              "batch_adjusted": use_batch, "df_residual": int(df), "pseudocount": pseudocount,
              "n_genes_input": int(fpkm.shape[0]), "n_genes_tested": int(xk.shape[0]),
              "n_padj_lt_0.05": int((res["padj_bh"] < 0.05).sum()), "flags": flags,
              "caveat": CAVEAT}
    return res, report
