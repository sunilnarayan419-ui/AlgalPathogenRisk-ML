from app.schemas import BreakEvenRequest, BreakEvenResponse

def calculate_break_even(data: BreakEvenRequest) -> BreakEvenResponse:
    """Scenario math only; inputs are assumptions, not measured biological effects."""
    avoided = data.baseline_collapse_probability * data.intervention_effectiveness * data.collapse_loss
    net = avoided - data.intervention_cost
    denominator = data.intervention_effectiveness * data.collapse_loss
    threshold = data.intervention_cost / denominator if denominator > 0 else None
    return BreakEvenResponse(
        expected_loss_avoided_per_batch=round(avoided, 2),
        net_expected_value_per_batch=round(net, 2),
        break_even_baseline_probability=round(threshold, 6) if threshold is not None else None,
        pilot_expected_net_value=round(net * data.pilot_batches, 2),
        economically_favourable_under_assumptions=net > 0,
        disclaimer="Illustrative expected-value calculation. Replace assumptions with validated facility-specific data."
    )
