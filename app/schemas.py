from pydantic import BaseModel, Field

class BreakEvenRequest(BaseModel):
    intervention_cost: float = Field(gt=0, description="Cost per treated batch")
    collapse_loss: float = Field(gt=0, description="Loss if a batch collapses")
    intervention_effectiveness: float = Field(ge=0, le=1, description="Assumed relative risk reduction")
    baseline_collapse_probability: float = Field(ge=0, le=1)
    pilot_batches: int = Field(default=1, ge=1)

class BreakEvenResponse(BaseModel):
    expected_loss_avoided_per_batch: float
    net_expected_value_per_batch: float
    break_even_baseline_probability: float | None
    pilot_expected_net_value: float
    economically_favourable_under_assumptions: bool
    disclaimer: str
