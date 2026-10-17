import pandas as pd
import pytest

from app.networks import analysis as na

RECS = [{"a": "A", "b": "B", "confidence": 0.9}, {"a": "B", "b": "C", "confidence": 0.4},
        {"a": "C", "b": "D"}, {"a": "E", "b": "F", "confidence": 0.8},
        {"a": "A", "b": "C", "confidence": 0.7}]


@pytest.fixture()
def g():
    return na.graph_from_edge_records(RECS, "SYNTHETIC_TEST", "0")


def test_summary_and_provenance(g):
    s = na.summarize(g)
    assert s["n_nodes"] == 6 and s["n_components"] == 2 and s["largest_component"] == 4
    assert s["top_degree"][0] == ("C", 3)
    assert s["edges_by_source"] == {"SYNTHETIC_TEST@0": 5}
    assert na.summarize(na.graph_from_edge_records([], "S", "1"))["n_nodes"] == 0


def test_duplicate_and_bad_records_raise():
    with pytest.raises(ValueError, match="record 1"):
        na.graph_from_edge_records([{"a": "A", "b": "B"}] * 2, "S", "1")
    with pytest.raises(ValueError, match="record 0"):
        na.graph_from_edge_records([{"a": "A"}], "S", "1")
    with pytest.raises(ValueError):
        na.graph_from_edge_records([{"a": "A", "b": "A"}], "S", "1")


def test_neighborhood_and_filter(g):
    assert sorted(na.neighborhood(g, "A", 1).nodes) == ["A", "B", "C"]
    with pytest.raises(KeyError):
        na.neighborhood(g, "ZZ")
    assert na.filter_by_confidence(g, 0.5).number_of_edges() == 4  # low-confidence B-C dropped


def test_overlay_de_modules_and_permutation_is_seeded(g):
    de = pd.DataFrame({"padj_bh": [.001, .01, .5, .9, .002, .003],
                       "log2_diff_a_minus_b": [2, 1.5, 0, 0, -1, 1]}, index=list("ABCDEF"))
    o1, o2 = na.overlay_de(g, de, n_perm=200), na.overlay_de(g, de, n_perm=200)
    assert [m["genes"] for m in o1["modules"]] == [["A", "B"], ["E", "F"]]
    assert o1["edge_enrichment"] == o2["edge_enrichment"]
    assert 0 < o1["edge_enrichment"]["permutation_p"] <= 1
