"""Machine-readable experiment specification (planning only, never observed results)."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field

import yaml

REQUIRED = ("objective", "hypothesis", "primary_endpoint", "experimental_unit",
            "biological_replicate_definition", "groups", "control_group",
            "primary_analysis", "sample_size_rationale", "randomization_method",
            "biosafety_statement")


@dataclass
class ExperimentSpec:
    objective: str = ""
    hypothesis: str = ""
    primary_endpoint: str = ""
    experimental_unit: str = ""
    biological_replicate_definition: str = ""
    groups: list[str] = field(default_factory=list)
    control_group: str = ""
    design: str = "completely_randomized"
    alpha: float = 0.05
    power: float = 0.8
    expected_effect_size: float | None = None
    primary_analysis: str = ""
    sample_size_rationale: str = ""
    randomization_method: str = ""
    randomization_seed: int | None = None
    inclusion_criteria: list[str] = field(default_factory=list)
    exclusion_criteria: list[str] = field(default_factory=list)
    secondary_analyses: list[str] = field(default_factory=list)
    biosafety_statement: str = ""  # containment, approvals; pathogen work is never assumed OK
    status: str = "planned_not_executed"

    def missing(self) -> list[str]:
        gaps = [f for f in REQUIRED if not getattr(self, f)]
        if self.groups and self.control_group and self.control_group not in self.groups:
            gaps.append("control_group (not among groups)")
        if len(self.groups) < 2:
            gaps.append("groups (need >= 2)")
        return gaps

    def validate(self) -> None:
        gaps = self.missing()
        if gaps:
            raise ValueError(f"Incomplete experiment specification; define: {sorted(set(gaps))}")
        if not (0 < self.alpha < 1 and 0 < self.power < 1):
            raise ValueError("alpha and power must be in (0, 1).")

    def to_dict(self) -> dict:
        self.validate()
        import app
        d = asdict(self)
        d["provenance"] = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                           "package_version": getattr(app, "__version__", "0.1.0"),
                           "note": "Specification of a FUTURE study; contains no observed data."}
        return d

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False)

    def to_markdown(self) -> str:
        d = self.to_dict()
        lines = ["# Experiment plan (not executed)", ""]
        for k, v in d.items():
            if k == "provenance":
                continue
            lines.append(f"- **{k.replace('_', ' ')}**: {v}")
        lines += ["", f"_Generated {d['provenance']['generated_utc']} — {d['provenance']['note']}_"]
        return "\n".join(lines)
