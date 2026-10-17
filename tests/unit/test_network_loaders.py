"""Synthetic STRING/BioGRID fixtures written to tmp files. Not biological evidence."""
import gzip
import zipfile

import networkx as nx
import pytest

from app.networks.graph import add_edge, read_graphml, write_graphml
from app.networks.loaders import (
    NetworkLoadError, default_gene_id, expression_overlap, load_biogrid_tab3,
    load_string_links, merge_graphs, restrict_to_genes,
)

STRING_HEADER = ("protein1 protein2 neighborhood fusion cooccurence coexpression "
                 "experimental database textmining combined_score")
STRING_ROWS = [
    "3055.Cre01.g000050.t1.1 3055.Cre01.g000100.t1.1 0 0 0 100 800 0 0 900",
    "3055.Cre01.g000100.t1.1 3055.Cre01.g000050.t1.1 0 0 0 100 800 0 0 900",   # reverse row
    "3055.Cre01.g000050.t1.2 3055.Cre01.g000100.t1.1 0 0 0 100 700 0 0 850",   # isoform duplicate
    "3055.Cre01.g000050.t1.1 3055.Cre01.g000050.t1.2 0 0 0 0 0 0 0 999",       # self after collapse
    "3055.Cre02.g000200.t1.1 3055.Cre01.g000100.t1.1 0 0 0 0 0 0 600 650",     # below threshold
    "3055.Cre03.g000300.t1.1 3055.Cre01.g000100.t1.1 0 0 0 0 0 750 0 750",     # curated
    "9999.Other.g1.t1.1 9999.Other.g2.t1.1 0 0 0 0 0 0 0 990",                 # other taxon
]


def _write(tmp_path, rows, header=STRING_HEADER, name="string.txt"):
    p = tmp_path / name
    p.write_text("\n".join([header, *rows]) + "\n")
    return p


def test_default_gene_id():
    assert default_gene_id("3055.Cre01.g000050.t1.1") == "Cre01.g000050"
    assert default_gene_id("Cre01.g000050.t1.2") == "Cre01.g000050"
    assert default_gene_id("Cre01.g000050") == "Cre01.g000050"


def test_string_loader_dedup_threshold_and_evidence(tmp_path):
    g, rep = load_string_links(_write(tmp_path, STRING_ROWS), source_version="test",
                               min_combined_score=700, taxon_id=3055)
    assert g.number_of_edges() == 2
    assert rep["n_rows_read"] == 7 and rep["n_other_taxon_skipped"] == 1
    assert rep["n_below_threshold"] == 1 and rep["n_self_pairs_after_normalisation"] == 1
    assert rep["n_rows_merged_as_duplicates"] == 2
    ((_, _, d1),) = [e for e in g.edges(data=True) if {e[0], e[1]} == {"Cre01.g000050", "Cre01.g000100"}]
    assert d1["confidence"] == pytest.approx(0.9) and d1["evidence_type"] == "experimental"
    assert d1["score_experimental"] == 800 and d1["source_db"] == "STRING"
    ((_, _, d2),) = [e for e in g.edges(data=True) if "Cre03.g000300" in e[:2]]
    assert d2["evidence_type"] == "curated"


def test_string_loader_gzip_and_combined_only(tmp_path):
    p = tmp_path / "links.txt.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("protein1 protein2 combined_score\n3055.A.t1 3055.B.t1 800\n")
    g, rep = load_string_links(p, source_version="t", id_normalizer=default_gene_id)
    assert g.number_of_edges() == 1 and rep["channels_in_file"] == []
    (_, _, d), = g.edges(data=True)
    assert d["evidence_type"] == "predicted"  # channel unknown -> not claimed as experimental


def test_string_loader_rejects_malformed(tmp_path):
    with pytest.raises(NetworkLoadError):
        load_string_links(_write(tmp_path, ["a b 1 2"]), source_version="t")        # field count
    with pytest.raises(NetworkLoadError):
        load_string_links(_write(tmp_path, ["a b 0 0 0 0 x 0 0 900"]), source_version="t")
    with pytest.raises(NetworkLoadError):
        load_string_links(_write(tmp_path, ["a b 0 0 0 0 0 0 0 1500"]), source_version="t")
    with pytest.raises(NetworkLoadError):
        load_string_links(_write(tmp_path, ["a b 5"], header="x y z"), source_version="t")
    with pytest.raises(ValueError):
        load_string_links(_write(tmp_path, []), source_version="t", min_combined_score=2000)


BIOGRID_HEADER = "\t".join(["#BioGRID Interaction ID", "Systematic Name Interactor A",
                            "Systematic Name Interactor B", "Official Symbol Interactor A",
                            "Official Symbol Interactor B", "Experimental System Type",
                            "Organism ID Interactor A", "Organism ID Interactor B"])
BIOGRID_ROWS = [
    "1\tCre01.g000050\tCre01.g000100\tA\tB\tphysical\t3055\t3055",
    "2\tCre01.g000100\tCre01.g000050\tB\tA\tphysical\t3055\t3055",
    "3\tCre01.g000050\tCre01.g000100\tA\tB\tgenetic\t3055\t3055",
    "4\t-\tCre01.g000100\t-\tB\tphysical\t3055\t3055",
    "5\tX\tY\tx\ty\tphysical\t9606\t9606",
    "6\tCre01.g000050\tCre01.g000050\tA\tA\tphysical\t3055\t3055",
]


def test_biogrid_loader(tmp_path):
    p = _write(tmp_path, BIOGRID_ROWS, header=BIOGRID_HEADER, name="bg.tab3.txt")
    g, rep = load_biogrid_tab3(p, source_version="4.4.test")
    assert g.number_of_edges() == 2 and rep["n_missing_identifier"] == 1
    assert rep["n_filtered_other_organism"] == 1 and rep["n_self_pairs"] == 1
    phys = [d for *_, d in g.edges(data=True) if d["interaction_type"] == "physical"][0]
    assert phys["evidence_ids"] == "1;2" and phys["evidence_type"] == "experimental"
    assert phys["confidence"] == -1.0  # not reported


def test_biogrid_zip_and_bad_header(tmp_path):
    z = tmp_path / "bg.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("bg.tab3.txt", "\n".join([BIOGRID_HEADER, BIOGRID_ROWS[0]]) + "\n")
    g, _ = load_biogrid_tab3(z, source_version="t")
    assert g.number_of_edges() == 1
    bad = _write(tmp_path, ["1\t2"], header="a\tb", name="bad.txt")
    with pytest.raises(NetworkLoadError):
        load_biogrid_tab3(bad, source_version="t")
    with pytest.raises(ValueError):
        load_biogrid_tab3(z, source_version="t", id_column="nonsense")


def test_merge_overlap_restrict_and_graphml_roundtrip(tmp_path):
    s, _ = load_string_links(_write(tmp_path, STRING_ROWS), source_version="t", taxon_id=3055)
    b, _ = load_biogrid_tab3(_write(tmp_path, BIOGRID_ROWS, header=BIOGRID_HEADER, name="b.txt"),
                             source_version="t")
    m = merge_graphs(s, b)
    assert m.number_of_edges() == s.number_of_edges() + b.number_of_edges()
    with pytest.raises(ValueError):
        merge_graphs(s, s)
    ov = expression_overlap(m, ["Cre01.g000050", "Cre01.g000100", "Cre99.g1"])
    assert ov["n_nodes_in_expression"] == 2 and ov["fraction_nodes_in_expression"] == pytest.approx(2 / 3)
    sub = restrict_to_genes(m, ["Cre01.g000050", "Cre01.g000100"])
    assert set(sub.nodes) == {"Cre01.g000050", "Cre01.g000100"}
    path = tmp_path / "m.graphml"
    write_graphml(m, path)  # extra scalar attributes must survive GraphML
    assert read_graphml(path).number_of_edges() == m.number_of_edges()


def test_add_edge_attributes_validation():
    g = nx.MultiGraph()
    kw = dict(source_db="T", source_version="0", interaction_type="x", evidence_type="predicted")
    add_edge(g, "A", "B", attributes={"score_x": 3}, **kw)
    with pytest.raises(ValueError):
        add_edge(g, "A", "C", attributes={"confidence": 0.1}, **kw)  # reserved key
    with pytest.raises(ValueError):
        add_edge(g, "A", "D", attributes={"bad": [1, 2]}, **kw)      # non-scalar
