from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExperimentSpecIn(BaseModel):
    objective: str = ""
    hypothesis: str = ""
    primary_endpoint: str = ""
    experimental_unit: str = ""
    biological_replicate_definition: str = ""
    groups: list[str] = Field(default_factory=list)
    control_group: str = ""
    design: str = "completely_randomized"
    alpha: float = Field(0.05, gt=0, lt=1)
    power: float = Field(0.8, gt=0, lt=1)
    expected_effect_size: float | None = None
    primary_analysis: str = ""
    sample_size_rationale: str = ""
    randomization_method: str = ""
    randomization_seed: int | None = None
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    secondary_analyses: list[str] = Field(default_factory=list)
    biosafety_statement: str = ""
    save_as: str | None = Field(None, description="Persist the complete plan under this name.")


class PowerRequest(BaseModel):
    endpoint: Literal["continuous", "binary", "time_to_event"]
    effect_size_d: float | None = None
    p1: float | None = None
    p2: float | None = None
    alpha: float = Field(0.05, gt=0, lt=1)
    power: float = Field(0.8, gt=0, lt=1)
    ratio: float = Field(1.0, gt=0)
    attrition: float = Field(0.0, ge=0, lt=1)
    n_comparisons: int = Field(1, ge=1)
    two_sided: bool = True


class RandomizeRequest(BaseModel):
    unit_ids: list[str] = Field(min_length=2, max_length=5000)
    groups: list[str] = Field(min_length=2)
    seed: int
    blocks: dict[str, str] | None = None


class AnalyzeRequest(BaseModel):
    values: list[float] = Field(min_length=4, max_length=100000)
    groups: list[str]
    group_a: str
    group_b: str
    unit_ids: list[str] | None = None
    confidence: float = Field(0.95, gt=0, lt=1)


class EvaluateRequest(BaseModel):
    """Genotype/strain-group baseline ONLY (not infection or collapse risk)."""
    matrix: list[list[float]] = Field(description="samples x features")
    labels: list[str]
    groups: list[str] | None = None
    seed: int = 42
    allow_ungrouped: bool = False


class BreakEvenV1(BaseModel):
    p: float = Field(ge=0, le=1, description="baseline failure probability (hypothetical)")
    L: float = Field(gt=0, description="loss given failure (currency)")
    C: float = Field(ge=0, description="intervention cost (currency)")
    e: float = Field(ge=0, le=1, description="relative reduction in failure probability")
    cycles: int = Field(1, ge=1)
    save_as: str | None = None


class SensitivityRequest(BaseModel):
    L: float = Field(gt=0)
    C: float = Field(ge=0)
    p_values: list[float] = Field(min_length=1, max_length=100)
    e_values: list[float] = Field(min_length=1, max_length=100)
    cycles: int = Field(1, ge=1)


class DatasetAuditResponse(BaseModel):
    dataset_version_id: int
    audit_id: int
    valid: bool
    sha256: str
    n_genes: int
    n_samples: int
    issue_codes: list[str]
