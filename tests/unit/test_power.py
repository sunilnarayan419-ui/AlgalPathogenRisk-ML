import pytest

from app.experiments.power import (UnsupportedDesignError, sample_size,
                                   sample_size_two_group_continuous, sample_size_two_proportions)


def test_continuous_matches_textbook_d05():
    # Cohen: d=0.5, alpha=.05 two-sided, power=.80 -> 64 per group
    r = sample_size_two_group_continuous(0.5)
    assert (r["n_group1"], r["n_group2"]) == (64, 64)
    assert r["assumptions"]["achieved_power"] >= 0.8


def test_attrition_and_bonferroni_increase_n():
    base = sample_size_two_group_continuous(0.8)["n_group1"]
    assert sample_size_two_group_continuous(0.8, n_comparisons=5)["n_group1"] > base
    r = sample_size_two_group_continuous(0.8, attrition=0.2)
    assert r["enrol_group1"] > r["n_group1"]


def test_proportions_textbook():
    assert sample_size_two_proportions(0.5, 0.7)["n_group1"] == 93


def test_invalid_inputs():
    with pytest.raises(ValueError):
        sample_size_two_group_continuous(0)
    with pytest.raises(ValueError):
        sample_size_two_proportions(0.5, 0.5)
    with pytest.raises(ValueError):
        sample_size_two_group_continuous(0.5, alpha=1.5)


def test_unsupported_design_is_explicit():
    with pytest.raises(UnsupportedDesignError):
        sample_size("time_to_event")
