"""Guardrail tests need no PyDESeq2; the model run is skipped when it is not installed.
All counts are SYNTHETIC. The manifest test uses the repository's real sample manifest."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.experiments.count_de import (
    ConfoundingError, DesignError, contrast_estimable, design_matrix, estimable_contrasts,
    filter_low_counts, log2_normalized, run_deseq2, size_factors,
)

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "metadata" / "sample_manifest.csv"


def _nb_counts(n_per=4, n_genes=300, n_de=20, fold=4.0, seed=0, batch=None):
    rng = np.random.default_rng(seed)
    base = rng.gamma(2.0, 100.0, n_genes)
    cols, data, grp = [], [], []
    for g in ("A", "B"):
        for r in range(n_per):
            mu = base.copy()
            if g == "B":
                mu[:n_de] *= fold
            depth = rng.uniform(0.7, 1.3)
            data.append(rng.negative_binomial(10, 10 / (10 + mu * depth)))
            cols.append(f"{g}{r}")
            grp.append(g)
    counts = pd.DataFrame(np.array(data).T, columns=cols,
                          index=[f"g{i}" for i in range(n_genes)])
    meta = pd.DataFrame({"group": grp}, index=cols)
    if batch is not None:
        meta["batch"] = batch
    return counts, meta


def test_size_factors_recover_depth():
    rng = np.random.default_rng(1)
    base = rng.gamma(5, 50, 500)
    depth = np.array([0.5, 1.0, 2.0])
    counts = pd.DataFrame(rng.poisson(np.outer(base, depth)), columns=["a", "b", "c"])
    sf = size_factors(counts)
    assert sf["c"] / sf["a"] == pytest.approx(4.0, rel=0.1)
    assert size_factors(counts).prod() == pytest.approx(1.0, rel=0.2)  # geometric-mean ~ 1
    assert log2_normalized(counts).shape == counts.shape
    with pytest.raises(DesignError):
        size_factors(pd.DataFrame({"a": [0, 1], "b": [1, 0]}))
    with pytest.raises(ValueError):
        size_factors(counts + 0.5)


def test_filter_low_counts():
    c = pd.DataFrame({"a": [0, 20, 5], "b": [0, 30, 5], "c": [1, 25, 5]}, index=["x", "y", "z"])
    kept, removed = filter_low_counts(c, min_count=10, min_samples=2)
    assert list(kept.index) == ["y"] and removed == 2
    with pytest.raises(ValueError):
        filter_low_counts(c, min_samples=0)


def test_estimable_nested_batch_is_refused():
    meta = pd.DataFrame({"group": list("AAAABBBB"), "batch": ["b1"] * 4 + ["b2"] * 4})
    assert design_matrix(meta, "group", "batch").shape == (8, 3)
    assert contrast_estimable(meta, "group", "A", "B", "batch") is False
    assert contrast_estimable(meta, "group", "A", "B", None) is True


def test_estimable_crossed_design():
    meta = pd.DataFrame({"group": list("AABBAABB"), "batch": ["b1"] * 4 + ["b2"] * 4})
    assert contrast_estimable(meta, "group", "A", "B", "batch") is True
    with pytest.raises(DesignError):
        contrast_estimable(meta, "group", "A", "Z", "batch")
    with pytest.raises(ValueError):
        contrast_estimable(meta, "group", "A", "A", "batch")


@pytest.mark.skipif(not MANIFEST.exists(), reason="sample manifest not present")
def test_gse128981_manifest_contrasts():
    meta = pd.read_csv(MANIFEST).set_index("sample_accession")
    table = estimable_contrasts(meta, "strain", "batch").set_index(["group_a", "group_b"])
    # Elow47 (WT, batch1 only) vs UVM11-C1 (complemented, batch2 only): no shared batch,
    # estimable only by bridging through UVM11, which exists in both batches.
    row = table.loc[("Elow47", "UVM11-C1")]
    assert not row["shared_batch"] and row["estimable_adjusted"] and row["bridged_only"]
    assert table.loc[("Elow47", "UVM11")]["shared_batch"]
    # Restricting to just those two strains makes batch inseparable:
    sub = meta[meta["strain"].isin(["Elow47", "UVM11-C1"])]
    assert contrast_estimable(sub, "strain", "Elow47", "UVM11-C1", "batch") is False


def test_run_deseq2_refuses_confounded_and_small_designs():
    counts, meta = _nb_counts(batch=["b1"] * 4 + ["b2"] * 4)  # A all b1, B all b2
    with pytest.raises(ConfoundingError):
        run_deseq2(counts, meta, "group", "A", "B", batch_col="batch")
    with pytest.raises(DesignError):
        run_deseq2(counts.iloc[:, [0, 4]], meta.iloc[[0, 4]], "group", "A", "B")  # n=1 per group
    with pytest.raises(ValueError):
        run_deseq2(counts, meta.iloc[::-1], "group", "A", "B")  # sample order mismatch
    with pytest.raises(ValueError):
        run_deseq2(counts + 0.5, meta, "group", "A", "B")       # not integer counts


def test_run_deseq2_detects_planted_effect():
    pytest.importorskip("pydeseq2")
    counts, meta = _nb_counts()
    res, report = run_deseq2(counts, meta, "group", "B", "A")
    assert "batch_not_modelled" in report["flags"]
    planted = [f"g{i}" for i in range(20)]
    assert res.loc[planted, "padj"].median() < 0.05
    assert (res.loc[planted, "log2FoldChange"] > 1).mean() > 0.8   # B up vs A (log2 4 = 2)
