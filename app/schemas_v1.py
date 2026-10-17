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


class DemoTrainRequest(BaseModel):
    """Trains on SYNTHETIC data to exercise the software. Not biological evidence."""
    seed: int = 42
    n_groups: int = Field(60, ge=20, le=500)


class PredictRequest(BaseModel):
    records: list[dict[str, float]] = Field(min_length=1, max_length=1000)


class DifferentialExpressionRequest(BaseModel):
    gene_ids: list[str]
    sample_ids: list[str]
    values: list[list[float]] = Field(description="genes x samples FPKM (non-negative)")
    groups: dict[str, str] = Field(description="sample id -> group")
    group_a: str
    group_b: str
    batches: dict[str, str] | None = None
    allow_unadjusted: bool = False
    top_n: int = Field(50, ge=1, le=1000)


class EdgeRecord(BaseModel):
    a: str
    b: str
    confidence: float | None = Field(None, ge=0, le=1)
    evidence_type: Literal["experimental", "curated", "predicted", "text_mining"] | None = None


class NetworkSummaryRequest(BaseModel):
    edges: list[EdgeRecord] = Field(min_length=1, max_length=50000)
    source_db: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    evidence_type: Literal["experimental", "curated", "predicted", "text_mining"] = "predicted"
    node: str | None = None
    radius: int = Field(1, ge=1, le=5)
    top_k: int = Field(10, ge=1, le=100)


class UncertaintyRequest(BaseModel):
    """Uniform assumption ranges (low, high) for each input; not measured data."""
    p: tuple[float, float]
    L: tuple[float, float]
    C: tuple[float, float]
    e: tuple[float, float]
    n: int = Field(20000, ge=100, le=200000)
    seed: int = 0
    cycles: int = Field(1, ge=1)
