import pandas as pd
import pytest

from app.experiments.randomization import (attach_technical_replicates,
                                           check_replicate_independence, randomize)
from app.experiments.spec import ExperimentSpec


def test_reproducible_and_balanced():
    units = [f"u{i}" for i in range(10)]
    a = randomize(units, ["ctl", "trt"], seed=1)
    b = randomize(units, ["ctl", "trt"], seed=1)
    assert a.equals(b)
    assert a["group"].value_counts().tolist() == [5, 5]
    assert not a.equals(randomize(units, ["ctl", "trt"], seed=2))


def test_blocked_balance_within_blocks():
    units = [f"u{i}" for i in range(8)]
    blocks = {u: ("b1" if i < 4 else "b2") for i, u in enumerate(units)}
    out = randomize(units, ["ctl", "trt"], seed=3, blocks=blocks)
    assert (out.groupby(["block", "group"]).size() == 2).all()


def test_duplicate_units_rejected():
    with pytest.raises(ValueError):
        randomize(["u1", "u1", "u2"], ["a", "b"], seed=0)


def test_technical_replicates_inherit_arm_and_unknown_rejected():
    asg = randomize(["u1", "u2"], ["a", "b"], seed=0)
    reps = pd.DataFrame({"unit_id": ["u1", "u1", "u2"], "meas": [1, 2, 3]})
    out = attach_technical_replicates(asg, reps)
    assert out.groupby("unit_id")["group"].nunique().max() == 1
    with pytest.raises(ValueError):
        attach_technical_replicates(asg, pd.DataFrame({"unit_id": ["zz"], "meas": [1]}))
    bad = pd.DataFrame({"u": ["u1", "u1"], "g": ["a", "b"]})
    with pytest.raises(ValueError):
        check_replicate_independence(bad, "u", "g")


def test_spec_requires_explicit_definitions_and_exports():
    with pytest.raises(ValueError):
        ExperimentSpec().to_yaml()
    spec = ExperimentSpec(objective="o", hypothesis="h", primary_endpoint="e",
                          experimental_unit="flask", biological_replicate_definition="independent flask",
                          groups=["ctl", "trt"], control_group="ctl", primary_analysis="Welch",
                          sample_size_rationale="assumed d=0.8", randomization_method="seeded",
                          biosafety_statement="IBC approval required before any challenge")
    assert "planned_not_executed" in spec.to_yaml()
    assert spec.to_markdown().startswith("# Experiment plan")
