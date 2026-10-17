import numpy as np
import pytest

from app.ml import pipeline as p
from app.ml.report import write_report
from app.services import analysis_service as svc


def test_report_contains_required_sections_and_synthetic_banner(tmp_path):
    df = p.make_demo_dataset()
    p.train_and_evaluate(df, p.TrainConfig(synthetic=True), out_dir=tmp_path)
    out = write_report(tmp_path / "evaluation_report.json", tmp_path / "r.md")
    text = out.read_text()
    for h in ("## Dataset", "## Methodology", "## Held-out test results", "## Error analysis",
              "## Limitations and leakage risks", "## Reproduce", "SYNTHETIC DATA"):
        assert h in text
    assert "dummy" in text.lower()


def _payload():
    rng = np.random.default_rng(0)
    return dict(gene_ids=[f"g{i}" for i in range(30)], sample_ids=[f"s{i}" for i in range(8)],
                values=rng.gamma(2, 10, (30, 8)).tolist(),
                groups={f"s{i}": "a" if i < 4 else "b" for i in range(8)},
                group_a="a", group_b="b", top_n=3)


def test_de_payload_ok_and_rejections():
    out = svc.de_from_payload(_payload())
    assert len(out["results"]) == 3 and "caveat" in out["report"]
    with pytest.raises(svc.PayloadError):
        svc.de_from_payload({**_payload(), "values": [[1.0]]})
    with pytest.raises(svc.PayloadError):
        svc.de_from_payload({**_payload(), "groups": {"s0": "a"}})


def test_network_payload():
    out = svc.network_from_payload(dict(edges=[{"a": "A", "b": "B"}, {"a": "B", "b": "C"}],
                                        source_db="S", source_version="1", node="A"))
    assert out["neighborhood"]["nodes"] == ["A", "B"]
    with pytest.raises(svc.PayloadError):
        svc.network_from_payload(dict(edges=[{"a": "A", "b": "B"}], source_db="S",
                                      source_version="1", node="Z"))
