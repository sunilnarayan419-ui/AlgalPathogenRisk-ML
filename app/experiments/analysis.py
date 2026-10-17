"""Statistical utilities for a two-group continuous endpoint (Welch) and FDR control."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats


def two_group_welch(values, groups, group_a: str, group_b: str,
                    unit_ids=None, confidence: float = 0.95) -> dict:
    """Welch t test, mean difference (a - b) with CI, and Hedges' g.

    If unit_ids is given they must be unique: repeated units are technical replicates
    or repeated measures and need an appropriate model, not this test.
    """
    values = np.asarray(values, dtype=float)
    groups = np.asarray(groups)
    if values.shape != groups.shape:
        raise ValueError("values and groups must have the same length.")
    if unit_ids is not None and len(set(unit_ids)) != len(list(unit_ids)):
        raise ValueError("Repeated unit IDs: observations are not independent; "
                         "average technical replicates or use a repeated-measures model.")
    if not np.isfinite(values).all():
        raise ValueError("values contain NaN/inf; handle missing data explicitly.")
    a, b = values[groups == group_a], values[groups == group_b]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Need at least 2 independent observations per group.")
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se2a, se2b = va / len(a), vb / len(b)
    se = math.sqrt(se2a + se2b)
    if se == 0:
        raise ValueError("Zero variance in both groups; test undefined.")
    diff = a.mean() - b.mean()
    df = (se2a + se2b) ** 2 / (se2a ** 2 / (len(a) - 1) + se2b ** 2 / (len(b) - 1))
    tcrit = stats.t.ppf(1 - (1 - confidence) / 2, df)
    t_stat = diff / se
    p = 2 * stats.t.sf(abs(t_stat), df)
    sp = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2))
    j = 1 - 3 / (4 * (len(a) + len(b)) - 9)
    return {"n_a": len(a), "n_b": len(b), "mean_difference": float(diff),
            "ci": (float(diff - tcrit * se), float(diff + tcrit * se)),
            "confidence": confidence, "t": float(t_stat), "df": float(df), "p_value": float(p),
            "hedges_g": float(j * diff / sp) if sp > 0 else None,
            "caveat": "Assumes independent biological units; normality not tested."}


def benjamini_hochberg(pvalues) -> np.ndarray:
    """BH step-up adjusted p-values (FDR)."""
    p = np.asarray(pvalues, dtype=float)
    if ((p < 0) | (p > 1) | np.isnan(p)).any():
        raise ValueError("p-values must be in [0, 1].")
    n = len(p)
    order = np.argsort(p)
    adj = p[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out
