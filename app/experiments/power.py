"""Sample-size and power calculations with explicit assumptions.

Methods: exact power of the two-sample equal-variance t test via the noncentral t
distribution (SciPy), and Cohen's arcsine effect size h for two proportions
(normal approximation). Anything else raises UnsupportedDesignError rather than
returning an unjustified number.
"""
from __future__ import annotations

import math

from scipy import stats


class UnsupportedDesignError(ValueError):
    """Requested design/endpoint combination has no implemented, justified method."""


def _check(alpha: float, power: float, ratio: float, attrition: float) -> None:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1).")
    if not 0 < power < 1:
        raise ValueError("power must be in (0, 1).")
    if ratio <= 0:
        raise ValueError("allocation ratio (n2/n1) must be > 0.")
    if not 0 <= attrition < 1:
        raise ValueError("attrition must be in [0, 1).")


def t_test_power(n1: int, n2: int, effect_size_d: float, alpha: float = 0.05,
                 two_sided: bool = True) -> float:
    """Exact power of the pooled two-sample t test for standardized difference d."""
    df = n1 + n2 - 2
    nc = effect_size_d * math.sqrt(n1 * n2 / (n1 + n2))
    if two_sided:
        tcrit = stats.t.ppf(1 - alpha / 2, df)
        return float(stats.nct.sf(tcrit, df, nc) + stats.nct.cdf(-tcrit, df, nc))
    tcrit = stats.t.ppf(1 - alpha, df)
    return float(stats.nct.sf(tcrit, df, nc))


def _result(n1: int, n2: int, attrition: float, **assumptions) -> dict:
    enrol1 = math.ceil(n1 / (1 - attrition))
    enrol2 = math.ceil(n2 / (1 - attrition))
    return {"n_group1": n1, "n_group2": n2,
            "enrol_group1": enrol1, "enrol_group2": enrol2,
            "total_enrolled": enrol1 + enrol2,
            "assumptions": {"attrition": attrition, **assumptions},
            "note": "Per-group counts are INDEPENDENT BIOLOGICAL units, not technical replicates."}


def sample_size_two_group_continuous(effect_size_d: float, alpha: float = 0.05,
                                     power: float = 0.8, ratio: float = 1.0,
                                     attrition: float = 0.0, two_sided: bool = True,
                                     n_comparisons: int = 1) -> dict:
    """Smallest n1 (n2 = ceil(ratio*n1)) reaching the target power; Bonferroni optional."""
    _check(alpha, power, ratio, attrition)
    if effect_size_d == 0:
        raise ValueError("effect_size_d must be non-zero.")
    if n_comparisons < 1:
        raise ValueError("n_comparisons must be >= 1.")
    adj_alpha = alpha / n_comparisons
    d = abs(effect_size_d)

    def ok(n1: int) -> bool:
        return t_test_power(n1, math.ceil(ratio * n1), d, adj_alpha, two_sided) >= power

    hi = 2
    while not ok(hi):
        hi *= 2
        if hi > 1_000_000:
            raise ValueError("Required sample size exceeds 1,000,000; check effect size.")
    lo = max(2, hi // 2)
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    n1, n2 = lo, math.ceil(ratio * lo)
    return _result(n1, n2, attrition, method="pooled two-sample t test, exact noncentral t",
                   alpha=alpha, alpha_adjusted=adj_alpha, n_comparisons=n_comparisons,
                   power=power, effect_size_d=effect_size_d, allocation_ratio=ratio,
                   two_sided=two_sided,
                   achieved_power=t_test_power(n1, n2, d, adj_alpha, two_sided))


def sample_size_two_proportions(p1: float, p2: float, alpha: float = 0.05,
                                power: float = 0.8, ratio: float = 1.0,
                                attrition: float = 0.0) -> dict:
    """Arcsine (Cohen's h) normal approximation, two-sided. Approximate for extreme p."""
    _check(alpha, power, ratio, attrition)
    for p in (p1, p2):
        if not 0 < p < 1:
            raise ValueError("Proportions must be strictly between 0 and 1.")
    if p1 == p2:
        raise ValueError("p1 and p2 must differ.")
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    n1 = math.ceil(z ** 2 * (1 + 1 / ratio) / h ** 2)
    n2 = math.ceil(ratio * n1)
    return _result(n1, n2, attrition, method="Cohen's h, normal approximation", alpha=alpha,
                   power=power, p1=p1, p2=p2, cohens_h=abs(h), allocation_ratio=ratio)


def sample_size(endpoint: str, **kwargs) -> dict:
    """Dispatch; unsupported endpoints (e.g. time-to-event) return a clear limitation."""
    if endpoint == "continuous":
        return sample_size_two_group_continuous(**kwargs)
    if endpoint == "binary":
        return sample_size_two_proportions(**kwargs)
    raise UnsupportedDesignError(
        f"No justified closed-form method implemented for endpoint '{endpoint}'. "
        "Use a simulation-based calculation specific to the design.")
