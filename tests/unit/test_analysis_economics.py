import numpy as np
import pytest
from scipy import stats

from app.experiments.analysis import benjamini_hochberg, two_group_welch
from app.services import economics_core as ec


def test_welch_matches_scipy():
    rng = np.random.default_rng(0)
    a, b = rng.normal(1, 1, 8), rng.normal(0, 2, 6)
    vals = np.r_[a, b]
    grp = np.array(["a"] * 8 + ["b"] * 6)
    r = two_group_welch(vals, grp, "a", "b")
    ref = stats.ttest_ind(a, b, equal_var=False)
    assert r["p_value"] == pytest.approx(ref.pvalue)
    assert r["t"] == pytest.approx(ref.statistic)
    assert r["ci"][0] < r["mean_difference"] < r["ci"][1]


def test_welch_rejects_repeated_units_and_small_n():
    with pytest.raises(ValueError):
        two_group_welch([1, 2, 3, 4], ["a", "a", "b", "b"], "a", "b", unit_ids=["u", "u", "v", "w"])
    with pytest.raises(ValueError):
        two_group_welch([1, 2, 3], ["a", "b", "b"], "a", "b")


def test_bh_known_values():
    adj = benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    assert adj.tolist() == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_economics_identities():
    p, L, C, e = 0.4, 1000, 100, 0.5
    assert ec.expected_loss_without(p, L) == 400
    assert ec.expected_cost_with(p, L, C, e) == 300
    assert ec.net_benefit(p, L, C, e) == 100 == ec.expected_loss_without(p, L) - ec.expected_cost_with(p, L, C, e)
    assert ec.net_benefit(p, L, C, e, cycles=3) == 300
    assert ec.break_even_probability(L, C, e)["p_star"] == pytest.approx(0.2)


def test_economics_boundaries():
    assert ec.break_even_probability(1000, 100, 0)["feasible"] is False
    assert ec.break_even_probability(1000, 600, 0.5)["feasible"] is False  # p* = 1.2
    assert ec.net_benefit(0, 1000, 100, 0.5) == -100
    for bad in (dict(p=1.2, L=1, C=1, e=0.5), dict(p=.5, L=0, C=1, e=.5),
                dict(p=.5, L=1, C=-1, e=.5), dict(p=.5, L=1, C=1, e=2)):
        with pytest.raises(ValueError):
            ec.net_benefit(**bad)


def test_sensitivity_and_bounds():
    grid = ec.sensitivity_grid(1000, 100, [0.1, 0.5], [0.2, 0.6])
    assert len(grid) == 4
    b = ec.net_benefit_bounds((0.1, 0.5), (800, 1200), (80, 120), (0.2, 0.6))
    assert b["lower"] < 0 < b["upper"]
