from app.experiments.spec import ExperimentSpec
from app.ml.baseline import RISK_MODEL_STATUS


def test_no_risk_model_is_claimed():
    assert RISK_MODEL_STATUS["available"] is False
    assert "genotype" in RISK_MODEL_STATUS["reason"].lower()


def test_biosafety_statement_is_mandatory():
    import pytest
    spec = ExperimentSpec(objective="o", hypothesis="h", primary_endpoint="e", experimental_unit="u",
                          biological_replicate_definition="b", groups=["a", "b"], control_group="a",
                          primary_analysis="p", sample_size_rationale="s", randomization_method="r")
    with pytest.raises(ValueError):
        spec.validate()
