import networkx as nx
import numpy as np
import pandas as pd
import pytest

from app.analysis.exploratory import log2_fpkm, pca_scores, qc_summary
from app.ml.baseline import RISK_MODEL_STATUS, evaluate_group_baseline
from app.networks.graph import add_edge, metrics, read_graphml, write_graphml

KW = dict(source_db="SYNTHETIC_TEST", source_version="0", interaction_type="assoc",
          evidence_type="predicted")


def test_network_validation_and_roundtrip(tmp_path):
    g = nx.MultiGraph()
    add_edge(g, "A", "B", confidence=0.7, evidence_ids=["x1"], **KW)
    with pytest.raises(ValueError):
        add_edge(g, "A", "B", **KW)  # duplicate
    with pytest.raises(ValueError):
        add_edge(g, "A", "C", confidence=1.5, **KW)
    with pytest.raises(ValueError):
        add_edge(g, "A", "C", **{**KW, "source_db": ""})
    with pytest.raises(ValueError):
        add_edge(g, "A", "C", **{**KW, "evidence_type": "vibes"})
    p = tmp_path / "g.graphml"
    write_graphml(g, p)
    g2 = read_graphml(p)
    assert g2.number_of_edges() == 1
    assert metrics(nx.MultiGraph())["n_nodes"] == 0


def _synthetic(n_per=6, seed=0):  # SYNTHETIC data, not biological evidence
    rng = np.random.default_rng(seed)
    genes = [f"g{i}" for i in range(40)]
    cols, data = [], []
    for grp, shift in (("A", 0), ("B", 3)):
        for r in range(n_per):
            v = rng.gamma(2, 5, 40)
            v[:10] += shift * 10
            data.append(v)
            cols.append(f"{grp}{r}")
    return pd.DataFrame(np.array(data).T, index=genes, columns=cols)


def test_exploratory_transform_does_not_mutate_and_pca():
    f = _synthetic()
    orig = f.copy()
    logged, meta = log2_fpkm(f)
    assert f.equals(orig) and meta["pseudocount"] == 1.0
    pca = pca_scores(logged)
    assert pca["scores"].shape == (12, 2)
    assert qc_summary(f).shape[0] == 12
    with pytest.raises(ValueError):
        log2_fpkm(f - 1000)


def test_baseline_grouped_and_refusals():
    f = _synthetic(n_per=6)
    logged, _ = log2_fpkm(f)
    X = logged.T
    y = np.array([c[0] for c in X.index])
    groups = np.array([c for c in X.index])  # each sample its own independent unit
    r = evaluate_group_baseline(X, y, groups=groups)
    assert r["status"] == "evaluated_exploratory" and "caveat" in r
    assert r["metrics"]["logistic_l2"]["balanced_accuracy"] >= r["metrics"]["dummy_most_frequent"]["balanced_accuracy"]
    assert evaluate_group_baseline(X, y, groups=groups) == r  # reproducible
    with pytest.raises(ValueError):
        evaluate_group_baseline(X, y)  # ungrouped refused
    tiny = evaluate_group_baseline(X.iloc[[0, 1, 6, 7]], y[[0, 1, 6, 7]], groups=groups[[0, 1, 6, 7]])
    assert tiny["status"] == "insufficient_data" and tiny["metrics"] is None
    with pytest.raises(ValueError):
        evaluate_group_baseline(X, np.array(["A"] * 12), groups=groups)
    assert RISK_MODEL_STATUS["available"] is False
