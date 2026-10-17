"""Count-based differential expression with design guardrails.

What is implemented here (numpy/pandas only, no heavy dependency):
  * median-of-ratios size factors, low-count filtering, log2 normalised counts
  * design-matrix construction and an exact *estimability* check for any pairwise contrast,
    so a comparison that is perfectly confounded with batch is refused instead of reported

What is delegated:
  * the negative-binomial model itself (dispersion shrinkage, Wald test, BH adjustment) is
    done by PyDESeq2 (``pip install "algae-culture-risk-prototype[de]"``), imported lazily.

Status: written without being executed. The PyDESeq2 call site tries the current keyword
(``design="~batch + condition"``) and falls back to the older ``design_factors=[...]``;
check it against the PyDESeq2 version you install.

Input must be RAW integer counts (see ``app.data.counts``). FPKM is rejected upstream.
"""
from __future__ import annotations

import importlib.metadata as md
import itertools
import re

import numpy as np
import pandas as pd


class ConfoundingError(ValueError):
    """The requested contrast cannot be separated from batch with the given samples."""


class DesignError(ValueError):
    pass


# ---------------------------------------------------------------- normalisation / filtering
def size_factors(counts: pd.DataFrame) -> pd.Series:
    """DESeq2 median-of-ratios size factors (genes in rows). Uses genes with a non-zero count
    in every sample; raises if there are none (then use a zero-tolerant estimator)."""
    _require_counts(counts)
    arr = counts.to_numpy(dtype=float)
    usable = (arr > 0).all(axis=1)
    if not usable.any():
        raise DesignError("No gene has a non-zero count in every sample; median-of-ratios "
                          "size factors are undefined (consider 'poscounts'-style estimators).")
    logs = np.log(arr[usable])
    log_geo_mean = logs.mean(axis=1, keepdims=True)
    sf = np.exp(np.median(logs - log_geo_mean, axis=0))
    return pd.Series(sf, index=counts.columns, name="size_factor")


def filter_low_counts(counts: pd.DataFrame, min_count: int = 10,
                      min_samples: int = 3) -> tuple[pd.DataFrame, int]:
    """Keep genes with >= min_count in >= min_samples samples. Returns (filtered, n_removed)."""
    if min_count < 0 or min_samples < 1:
        raise ValueError("min_count must be >= 0 and min_samples >= 1.")
    keep = (counts >= min_count).sum(axis=1) >= min_samples
    return counts.loc[keep], int((~keep).sum())


def log2_normalized(counts: pd.DataFrame, pseudocount: float = 1.0) -> pd.DataFrame:
    """log2(count / size_factor + pseudocount) for exploration (PCA/heatmaps), not for testing."""
    sf = size_factors(counts)
    return np.log2(counts.div(sf, axis=1) + pseudocount)


def _require_counts(counts: pd.DataFrame) -> None:
    if counts.empty:
        raise ValueError("Empty count matrix.")
    arr = counts.to_numpy(dtype=float)
    if not np.isfinite(arr).all() or (arr < 0).any():
        raise ValueError("Counts must be finite and non-negative.")
    if not np.allclose(arr, np.round(arr)):
        raise ValueError("Counts must be integers; this looks like normalised data.")


# ---------------------------------------------------------------- design / estimability
def design_matrix(meta: pd.DataFrame, group_col: str,
                  batch_col: str | None = None) -> pd.DataFrame:
    """Intercept + treatment-coded group dummies (+ batch dummies). Reference = first sorted level."""
    if group_col not in meta.columns:
        raise DesignError(f"metadata lacks {group_col!r}")
    parts = [pd.Series(1.0, index=meta.index, name="intercept")]
    g = meta[group_col].astype(str)
    for lvl in sorted(g.unique())[1:]:
        parts.append((g == lvl).astype(float).rename(f"group[{lvl}]"))
    if batch_col is not None:
        if batch_col not in meta.columns:
            raise DesignError(f"metadata lacks {batch_col!r}")
        b = meta[batch_col].astype(str)
        for lvl in sorted(b.unique())[1:]:
            parts.append((b == lvl).astype(float).rename(f"batch[{lvl}]"))
    return pd.concat(parts, axis=1)


def contrast_estimable(meta: pd.DataFrame, group_col: str, group_a: str, group_b: str,
                       batch_col: str | None = None) -> bool:
    """True iff (mean_a - mean_b) is estimable in the additive model ~ batch + group.

    A contrast vector c is estimable iff it lies in the row space of the design matrix X,
    i.e. rank(X) == rank([X; c]).
    """
    g = meta[group_col].astype(str)
    if group_a == group_b:
        raise ValueError("group_a and group_b must differ.")
    for lvl in (group_a, group_b):
        if lvl not in set(g):
            raise DesignError(f"group {lvl!r} not present in metadata")
    x = design_matrix(meta, group_col, batch_col)
    c = pd.Series(0.0, index=x.columns)
    if f"group[{group_a}]" in c.index:
        c[f"group[{group_a}]"] += 1.0
    if f"group[{group_b}]" in c.index:
        c[f"group[{group_b}]"] -= 1.0
    xv = x.to_numpy()
    r_x = np.linalg.matrix_rank(xv)
    r_xc = np.linalg.matrix_rank(np.vstack([xv, c.to_numpy()]))
    return bool(r_x == r_xc)


def estimable_contrasts(meta: pd.DataFrame, group_col: str, batch_col: str | None = None,
                        min_replicates: int = 2) -> pd.DataFrame:
    """Audit every pair of groups. Columns:

    ``estimable_adjusted``  estimable when batch is in the model (all samples used)
    ``shared_batch``        both groups have samples in at least one common batch
    ``bridged_only``        estimable only through other groups sharing batches
                            (rests on an additive, genotype-independent batch effect)
    ``enough_replicates``   both groups have >= min_replicates samples
    """
    g = meta[group_col].astype(str)
    b = meta[batch_col].astype(str) if batch_col else pd.Series("all", index=meta.index)
    rows = []
    for a, c in itertools.combinations(sorted(g.unique()), 2):
        shared = bool(set(b[g == a]) & set(b[g == c]))
        est = contrast_estimable(meta, group_col, a, c, batch_col) if batch_col else True
        rows.append({"group_a": a, "group_b": c, "n_a": int((g == a).sum()),
                     "n_b": int((g == c).sum()),
                     "batches_a": ",".join(sorted(set(b[g == a]))),
                     "batches_b": ",".join(sorted(set(b[g == c]))),
                     "shared_batch": shared, "estimable_adjusted": est,
                     "bridged_only": bool(est and not shared),
                     "enough_replicates": bool(min(int((g == a).sum()),
                                                   int((g == c).sum())) >= min_replicates)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the DE run
def _safe_labels(values: pd.Series, prefix: str) -> dict[str, str]:
    mapping = {v: f"{prefix}_" + re.sub(r"[^0-9A-Za-z_]", "_", v) for v in sorted(values.unique())}
    if len(set(mapping.values())) != len(mapping):
        raise DesignError(f"labels in {prefix!r} collide after sanitising: {sorted(mapping)}")
    return mapping


def run_deseq2(counts: pd.DataFrame, meta: pd.DataFrame, group_col: str, group_a: str,
               group_b: str, batch_col: str | None = None, use_all_samples: bool = False,
               allow_unadjusted: bool = False, min_count: int = 10, min_samples: int = 3,
               min_replicates: int = 2, alpha: float = 0.05) -> tuple[pd.DataFrame, dict]:
    """Wald test of group_a vs group_b (log2FC = a - b) with PyDESeq2.

    ``meta`` must be indexed by sample id in the same order as ``counts.columns``
    (see :func:`app.data.counts.align_metadata`). By default only samples of the two compared
    groups are modelled; ``use_all_samples=True`` models every sample so that other groups can
    bridge batches (flagged in the report). A contrast that cannot be separated from batch
    raises :class:`ConfoundingError` unless ``allow_unadjusted=True``, which drops the batch
    term and marks the result ``batch_confounded``.
    """
    _require_counts(counts)
    if list(meta.index) != list(counts.columns):
        raise ValueError("meta must be indexed by sample id in the same order as counts columns.")
    g_all = meta[group_col].astype(str)
    for lvl in (group_a, group_b):
        if lvl not in set(g_all):
            raise DesignError(f"group {lvl!r} not in metadata")
    if group_a == group_b:
        raise ValueError("group_a and group_b must differ.")

    sel = meta.index if use_all_samples else meta.index[g_all.isin([group_a, group_b])]
    m = meta.loc[sel].copy()
    c = counts[list(sel)]
    g = m[group_col].astype(str)
    n_a, n_b = int((g == group_a).sum()), int((g == group_b).sum())
    if min(n_a, n_b) < min_replicates:
        raise DesignError(f"need >= {min_replicates} samples per group; got {n_a} and {n_b}.")

    flags: list[str] = []
    use_batch = False
    if batch_col is None:
        flags.append("batch_not_modelled")
    else:
        if m[batch_col].astype(str).nunique() > 1:
            if contrast_estimable(m, group_col, group_a, group_b, batch_col):
                use_batch = True
                shared = (set(m.loc[g == group_a, batch_col].astype(str))
                          & set(m.loc[g == group_b, batch_col].astype(str)))
                if not shared:
                    flags.append("bridged_through_other_groups_assumes_additive_batch_effect")
            elif allow_unadjusted:
                flags.append("batch_confounded")
            else:
                raise ConfoundingError(
                    f"{group_a!r} vs {group_b!r} cannot be separated from {batch_col!r} with "
                    "these samples (the groups share no batch and nothing bridges them). "
                    "Compare within a batch, add a bridging design, or pass "
                    "allow_unadjusted=True to accept a batch-confounded result.")
    c, n_removed = filter_low_counts(c, min_count, min_samples)
    if c.shape[0] == 0:
        raise DesignError("No genes pass the low-count filter.")

    cond_map = _safe_labels(g, "g")
    model_meta = pd.DataFrame({"condition": g.map(cond_map).to_numpy()}, index=m.index)
    factors = ["condition"]
    if use_batch:
        model_meta["batch"] = m[batch_col].astype(str).map(_safe_labels(m[batch_col].astype(str), "b")).to_numpy()
        factors = ["batch", "condition"]

    try:
        from pydeseq2.dds import DeseqDataSet
        from pydeseq2.ds import DeseqStats
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise ImportError('PyDESeq2 is required: pip install "pydeseq2"  '
                          "(or pip install -e .[de])") from exc

    design = "~" + " + ".join(factors)
    data = c.T.astype("int64")
    try:
        dds = DeseqDataSet(counts=data, metadata=model_meta, design=design)
    except TypeError:  # older PyDESeq2 API
        dds = DeseqDataSet(counts=data, metadata=model_meta, design_factors=factors)
    dds.deseq2()
    stats = DeseqStats(dds, contrast=["condition", cond_map[group_a], cond_map[group_b]],
                       alpha=alpha)
    stats.summary()
    res = stats.results_df.copy()
    res.index.name = "gene_id"
    res = res.sort_values("padj", na_position="last")

    try:
        version = md.version("pydeseq2")
    except md.PackageNotFoundError:  # pragma: no cover
        version = "unknown"
    report = {"method": "PyDESeq2 Wald test (negative binomial GLM)", "pydeseq2_version": version,
              "design": design, "contrast": f"{group_a} vs {group_b} (log2FC = a - b)",
              "n_samples_a": n_a, "n_samples_b": n_b, "n_samples_modelled": int(len(sel)),
              "n_genes_input": int(counts.shape[0]), "n_genes_tested": int(c.shape[0]),
              "n_genes_removed_low_count": n_removed,
              "n_padj_below_alpha": int((res["padj"] < alpha).sum()), "alpha": alpha,
              "flags": flags,
              "caveat": ("Differences between strains/genotypes in this dataset are observational "
                         "and do not measure infection or culture-collapse risk. With few "
                         "replicates and partly inferred batches, treat hits as hypotheses.")}
    return res, report
