"""Uses the REAL GSE128981 series-matrix metadata (tests/fixtures), not synthetic data."""
from pathlib import Path

from app.services.metadata import audit_geo_series_matrix, build_sample_manifest

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "GSE128981_series_matrix.txt"


def test_real_metadata_structure():
    audit = audit_geo_series_matrix(FIX)
    assert audit["accession"] == "GSE128981"
    assert audit["sample_count_from_accessions"] == 21
    assert audit["expression_matrix_has_gene_rows"] is False  # as documented in the brief
    m = build_sample_manifest(audit, gse128981_batch_rule=True)
    assert m["strain"].value_counts().to_dict() == {"UVM11": 7, "Elow47": 4, "UVM4": 4,
                                                    "UVM11-C1": 3, "UVM11-C9": 3}
    assert m["batch"].value_counts().to_dict() == {"batch1": 12, "batch2": 9}
    # genotype is confounded with batch: WT only in batch1, complemented only in batch2
    assert set(m.loc[m.genotype == "SRTA WT", "batch"]) == {"batch1"}
    assert set(m.loc[m.genotype == "SRTA complemented", "batch"]) == {"batch2"}
    assert set(m.loc[m.strain == "UVM11", "batch"]) == {"batch1", "batch2"}


def test_unresolved_when_rule_not_applied():
    m = build_sample_manifest(audit_geo_series_matrix(FIX))
    assert (m["batch"] == "unresolved").all()
