# Economic decision support (hypothetical)

EL0 = pL; EL1 = C + p(1-e)L; NB = peL - C; p* = C/(eL) (feasible only if p* <= 1; undefined for e = 0).
Multi-cycle = cycles x NB under independent identical cycles. `net_benefit_bounds` gives the exact range over
input intervals. `compare_interventions` ranks options by NB at a given (p, L).

**Uncertainty:** `monte_carlo_net_benefit` draws each input from a *uniform assumption range*, returning the
mean, 5/50/95% quantiles, P(NB>0) and **EVPI** = E[max(NB,0)] - max(E[NB],0), the most that resolving all input
uncertainty could be worth for the choice intervene vs do nothing. Verified against the analytic case
NB = 50p - 10, p ~ U(0, 0.4): EVPI = 2.5. Endpoint: `POST /api/v1/economics/uncertainty`.

Units/currency/time horizon are whatever the caller uses consistently. All inputs are assumptions; nothing is
estimated from GSE128981, and results are not real operating costs. Economic thresholds are kept separate from
any scientific score.
