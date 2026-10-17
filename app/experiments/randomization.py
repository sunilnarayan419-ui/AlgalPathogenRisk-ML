"""Seeded randomization at the level of BIOLOGICAL units."""
from __future__ import annotations

import numpy as np
import pandas as pd


def randomize(unit_ids: list[str], groups: list[str], seed: int,
              blocks: dict[str, str] | None = None) -> pd.DataFrame:
    """Balanced assignment (group sizes differ by at most 1 within each block).

    unit_ids must be unique independent biological units. Repeated IDs (e.g. technical
    replicates of one culture) are rejected so they cannot be randomized independently.
    blocks optionally maps unit_id -> block label (permuted-block randomization).
    """
    if len(set(unit_ids)) != len(unit_ids):
        dups = sorted({u for u in unit_ids if unit_ids.count(u) > 1})
        raise ValueError(f"Duplicate unit IDs {dups}: technical replicates or repeated "
                         "measurements must not be randomized as independent units.")
    if len(groups) < 2 or len(set(groups)) != len(groups):
        raise ValueError("Provide at least two distinct group labels.")
    if blocks is not None and set(blocks) != set(unit_ids):
        raise ValueError("blocks must contain exactly the same unit IDs.")
    rng = np.random.default_rng(seed)
    labelled = {u: (blocks[u] if blocks else "all") for u in unit_ids}
    rows = []
    for block in sorted(set(labelled.values())):
        members = [u for u in unit_ids if labelled[u] == block]
        order = list(rng.permutation(len(members)))
        glabels = list(rng.permutation(groups))
        for rank, idx in enumerate(order):
            rows.append({"unit_id": members[idx], "block": block,
                         "group": glabels[rank % len(groups)]})
    out = pd.DataFrame(rows)
    out.attrs.update({"seed": seed, "method": "permuted-block" if blocks else "complete-balanced"})
    return out


def check_replicate_independence(table: pd.DataFrame, unit_col: str, group_col: str) -> None:
    """Raise if a biological unit appears in more than one arm."""
    arms = table.groupby(unit_col)[group_col].nunique()
    bad = arms[arms > 1].index.tolist()
    if bad:
        raise ValueError(f"Units assigned to multiple groups (not independent): {bad}")


def attach_technical_replicates(assignments: pd.DataFrame, replicates: pd.DataFrame,
                                unit_col: str = "unit_id") -> pd.DataFrame:
    """Give technical replicates the arm of their parent biological unit."""
    unknown = set(replicates[unit_col]) - set(assignments["unit_id"])
    if unknown:
        raise ValueError(f"Replicates reference unknown biological units: {sorted(unknown)}")
    return replicates.merge(assignments[["unit_id", "group"]], left_on=unit_col,
                            right_on="unit_id", how="left", suffixes=("", "_assigned"))
