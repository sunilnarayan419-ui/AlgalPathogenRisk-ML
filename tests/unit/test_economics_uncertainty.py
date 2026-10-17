import pytest

from app.services import economics_core as ec


def test_mean_and_evpi_match_analytic_values():
    r = ec.monte_carlo_net_benefit((0, .4), (100, 100), (10, 10), (.5, .5), n=400000, seed=2)
    assert abs(r["mean_net_benefit"]) < 0.1            # NB = 50p - 10, p~U(0,.4) -> mean 0
    assert abs(r["evpi"] - 2.5) < 0.05                 # analytic EVPI = 2.5
    assert abs(r["prob_net_benefit_positive"] - 0.5) < 0.01


def test_always_beneficial_case_has_zero_evpi_and_is_reproducible():
    a = ec.monte_carlo_net_benefit((.2, .4), (100, 100), (10, 10), (.5, .5), seed=1)
    b = ec.monte_carlo_net_benefit((.2, .4), (100, 100), (10, 10), (.5, .5), seed=1)
    assert a == b and a["evpi"] == pytest.approx(0, abs=1e-9) and a["prob_net_benefit_positive"] == 1


def test_invalid_ranges_rejected():
    with pytest.raises(ValueError, match="low > high"):
        ec.monte_carlo_net_benefit((.5, .1), (1, 1), (0, 0), (.5, .5))
    with pytest.raises(ValueError):
        ec.monte_carlo_net_benefit((0, 2), (1, 1), (0, 0), (.5, .5))
    with pytest.raises(ValueError, match="n must"):
        ec.monte_carlo_net_benefit((0, .1), (1, 1), (0, 0), (.5, .5), n=10)


def test_compare_interventions_ranks_by_net_benefit():
    r = ec.compare_interventions({"x": {"C": 10, "e": .5}, "y": {"C": 30, "e": .9}}, p=.3, L=100)
    assert [o["name"] for o in r] == ["x", "y"] and r[0]["net_benefit"] == pytest.approx(5)
