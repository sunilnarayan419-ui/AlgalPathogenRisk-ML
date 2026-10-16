from app.schemas import BreakEvenRequest
from app.services.economics import calculate_break_even

def test_positive_expected_value():
    req = BreakEvenRequest(intervention_cost=100, collapse_loss=1000,
        intervention_effectiveness=0.5, baseline_collapse_probability=0.4, pilot_batches=10)
    result = calculate_break_even(req)
    assert result.expected_loss_avoided_per_batch == 200
    assert result.net_expected_value_per_batch == 100
    assert result.pilot_expected_net_value == 1000
    assert result.economically_favourable_under_assumptions is True

def test_zero_effectiveness():
    req = BreakEvenRequest(intervention_cost=100, collapse_loss=1000,
        intervention_effectiveness=0, baseline_collapse_probability=0.4)
    result = calculate_break_even(req)
    assert result.break_even_baseline_probability is None
    assert result.economically_favourable_under_assumptions is False
