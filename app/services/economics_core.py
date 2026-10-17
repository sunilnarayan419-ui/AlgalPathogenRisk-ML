"""One-cycle expected-loss model (assumption-driven; NOT estimated from GSE128981).

p = baseline failure probability, L = loss given failure, C = intervention cost,
e = relative reduction in failure probability (p -> p(1-e)).
EL0 = pL;  EL1 = C + p(1-e)L;  NB = EL0 - EL1 = peL - C;  p* = C/(eL).
"""
from __future__ import annotations

import itertools

DISCLAIMER = "Hypothetical inputs; outputs are scenario arithmetic, not measured returns."


def _validate(p=None, L=None, C=None, e=None) -> None:
    if p is not None and not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1].")
    if L is not None and L <= 0:
        raise ValueError("L must be > 0.")
    if C is not None and C < 0:
        raise ValueError("C must be >= 0.")
    if e is not None and not 0 <= e <= 1:
        raise ValueError("e must be in [0, 1].")


def expected_loss_without(p: float, L: float) -> float:
    _validate(p=p, L=L)
    return p * L


def expected_cost_with(p: float, L: float, C: float, e: float) -> float:
    _validate(p, L, C, e)
    return C + p * (1 - e) * L


def net_benefit(p: float, L: float, C: float, e: float, cycles: int = 1) -> float:
    """peL - C per cycle; cycles>1 assumes independent, identical cycles."""
    _validate(p, L, C, e)
    if cycles < 1:
        raise ValueError("cycles must be >= 1.")
    return cycles * (p * e * L - C)


def break_even_probability(L: float, C: float, e: float) -> dict:
    _validate(L=L, C=C, e=e)
    if e == 0:
        return {"p_star": None, "feasible": False,
                "reason": "e = 0: the intervention cannot reduce loss, so it cannot break even."}
    if C == 0:
        return {"p_star": 0.0, "feasible": True, "reason": "Free intervention."}
    p_star = C / (e * L)
    if p_star > 1:
        return {"p_star": p_star, "feasible": False,
                "reason": "p* > 1: no failure probability makes the intervention break even."}
    return {"p_star": p_star, "feasible": True, "reason": "ok"}


def sensitivity_grid(L: float, C: float, p_values, e_values, cycles: int = 1) -> list[dict]:
    return [{"p": p, "e": e, "net_benefit": net_benefit(p, L, C, e, cycles)}
            for p, e in itertools.product(p_values, e_values)]


def net_benefit_bounds(p: tuple[float, float], L: tuple[float, float], C: tuple[float, float],
                       e: tuple[float, float]) -> dict:
    """Exact range of NB over (low, high) intervals: NB rises with p, e, L and falls with C."""
    return {"lower": net_benefit(p[0], L[0], C[1], e[0]),
            "upper": net_benefit(p[1], L[1], C[0], e[1]), "disclaimer": DISCLAIMER}
