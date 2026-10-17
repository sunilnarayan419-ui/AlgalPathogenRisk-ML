"""Streaming GEO series-matrix parser, measurement-type detection and expression QC.

* Handles .gz or plain text, ``!`` metadata lines, quoted tab-delimited records, and the
  ``!series_matrix_table_begin/_end`` markers. Files are read once, line by line.
* A truncated file (begin marker without end marker) is an error, not a silent success.
* An empty expression table (as in the supplied GSE128981 file) is reported explicitly;
  nothing is invented to fill it.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class GeoParseError(ValueError):
    """Malformed or truncated GEO series-matrix file."""


@dataclass
class GeoSeries:
    accession: str | None
    series: dict[str, list[str]]
    samples: pd.DataFrame                 # one row per sample; characteristics split into columns
    expression: pd.DataFrame | None       # genes x samples, None when the table is empty
    provenance: dict[str, Any] = field(default_factory=dict)


def _open(path: Path) -> io.TextIOBase:
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def _split(line: str) -> list[str]:
    return [c.strip().strip('"') for c in line.rstrip("\r\n").split("\t")]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_geo_series_matrix(path: str | Path) -> GeoSeries:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found.")
    series: dict[str, list[str]] = defaultdict(list)
    sample_fields: dict[str, list[list[str]]] = defaultdict(list)
    header: list[str] | None = None
    rows: list[list[str]] = []
    begun = ended = False
    n_lines = 0
    try:
        with _open(path) as fh:
            for line in fh:
                n_lines += 1
                if not line.strip():
                    continue
                if line.startswith("!series_matrix_table_begin"):
                    begun = True
                    continue
                if line.startswith("!series_matrix_table_end"):
                    ended = True
                    continue
                if begun and not ended:
                    cells = _split(line)
                    if header is None:
                        header = cells
                    else:
                        rows.append(cells)
                elif line.startswith("!Series_"):
                    series[line.split("\t", 1)[0][1:]].extend(_split(line)[1:])
                elif line.startswith("!Sample_"):
                    sample_fields[line.split("\t", 1)[0][1:]].append(_split(line)[1:])
    except (OSError, EOFError) as exc:
        raise GeoParseError(f"cannot read {path}: {exc}") from exc
    if begun and not ended:
        raise GeoParseError("expression table begin marker without end marker (truncated file).")
    if "Sample_geo_accession" not in sample_fields:
        raise GeoParseError("no !Sample_geo_accession line; not a GEO series-matrix file.")

    ids = sample_fields["Sample_geo_accession"][0]
    n = len(ids)
    if len(set(ids)) != n:
        raise GeoParseError("duplicate sample accessions in metadata.")
    cols: dict[str, list[str]] = {"sample_accession": ids}
    for name, lines in sample_fields.items():
        for i, vals in enumerate(lines):
            if len(vals) != n:
                raise GeoParseError(f"{name} has {len(vals)} values for {n} samples.")
            if name == "Sample_characteristics_ch1":
                for j, v in enumerate(vals):
                    k, sep, val = v.partition(":")
                    key = "char_" + re.sub(r"\W+", "_", k.strip().lower()) if sep else f"char_{i}"
                    cols.setdefault(key, [""] * n)[j] = val.strip() if sep else v
            else:
                key = name.removeprefix("Sample_").lower() + (f"_{i + 1}" if i else "")
                cols[key] = vals
    samples = pd.DataFrame(cols)

    expression = None
    if header is not None and rows:
        if len(header) < 2:
            raise GeoParseError("expression header has no sample columns.")
        bad = [i for i, r in enumerate(rows) if len(r) != len(header)]
        if bad:
            raise GeoParseError(f"{len(bad)} expression rows have the wrong number of fields "
                                f"(first at data row {bad[0] + 1}).")
        expression = pd.DataFrame(rows, columns=header).set_index(header[0])
        if set(expression.columns) != set(ids):
            raise GeoParseError("expression columns do not match !Sample_geo_accession.")
        expression = expression.apply(pd.to_numeric, errors="coerce")[ids]
    acc = (series.get("Series_geo_accession") or [None])[0]
    return GeoSeries(acc, dict(series), samples, expression,
                     {"path": str(path), "sha256": sha256(path), "lines_read": n_lines,
                      "table_markers": begun and ended, "n_expression_rows": len(rows)})


def classify_measurement(values: pd.DataFrame) -> dict[str, Any]:
    """Heuristic only: says what the values LOOK like. Confirm against the series metadata."""
    a = values.to_numpy(dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"kind": "unknown", "reason": "no finite values"}
    nonneg = bool((a >= 0).all())
    integer = bool(np.allclose(a, np.round(a)))
    mx = float(a.max())
    if nonneg and integer and mx > 20:
        kind, why = "raw_counts_like", "non-negative integers with large range"
    elif not nonneg or mx < 25 and not integer and (a < 0).any():
        kind, why = "log_transformed_like", "negative or small-range values"
    elif nonneg and not integer and mx > 25:
        kind, why = "normalized_abundance_like", "non-integer non-negative values (e.g. FPKM/TPM)"
    elif mx <= 25:
        kind, why = "log_transformed_like", "values all <= 25 (typical of log2 data)"
    else:
        kind, why = "unknown", "ambiguous"
    return {"kind": kind, "reason": why, "all_integer": integer, "min": float(a.min()), "max": mx,
            "count_based_methods_valid": kind == "raw_counts_like"}


def expression_qc(expr: pd.DataFrame, min_value: float = 1.0) -> dict[str, Any]:
    """Machine-readable QC for a genes x samples matrix (rows = features)."""
    if expr.shape[0] == 0 or expr.shape[1] == 0:
        raise ValueError("empty expression matrix.")
    dup_genes = expr.index[expr.index.duplicated()].unique().tolist()
    dup_samples = expr.columns[expr.columns.duplicated()].unique().tolist()
    n_missing = int(expr.isna().sum().sum())
    clean = expr.fillna(0)
    logged = np.log2(clean.clip(lower=0) + 1)
    med = logged.median()
    mad = float((med - med.median()).abs().median()) or 1e-9
    z = (med - med.median()) / (1.4826 * mad)
    corr = logged.corr()
    mean_corr = (corr.sum() - 1) / max(corr.shape[0] - 1, 1)
    return {
        "n_features": int(expr.shape[0]), "n_samples": int(expr.shape[1]),
        "n_missing": n_missing, "duplicate_feature_ids": dup_genes[:10],
        "n_duplicate_features": len(dup_genes), "duplicate_sample_ids": dup_samples,
        "n_negative": int((expr < 0).sum().sum()),
        "all_zero_features": int((clean == 0).all(axis=1).sum()),
        "zero_fraction": float((clean == 0).to_numpy().mean()),
        "features_detected_ge_min": {c: int((clean[c] >= min_value).sum()) for c in clean.columns},
        "sample_median_log2": {c: float(v) for c, v in med.items()},
        "outlier_samples_median_robust_z_gt_3.5": [c for c, v in z.items() if abs(v) > 3.5],
        "low_correlation_samples_mean_r_lt_0.8": [c for c, v in mean_corr.items() if v < 0.8],
        "measurement": classify_measurement(expr),
    }


def check_metadata_alignment(samples: pd.DataFrame, expr: pd.DataFrame | None) -> dict[str, Any]:
    if expr is None:
        return {"aligned": None, "reason": "no expression matrix to align"}
    a, b = set(samples["sample_accession"]), set(expr.columns)
    return {"aligned": a == b, "only_in_metadata": sorted(a - b), "only_in_matrix": sorted(b - a)}


def suitability(samples: pd.DataFrame, expr: pd.DataFrame | None,
                group_col: str = "char_genotype") -> dict[str, Any]:
    """What the data can and cannot support. Never infers labels."""
    sizes = (samples[group_col].value_counts().to_dict() if group_col in samples else {})
    can, cannot = [], ["pathogen-risk or culture-collapse prediction (no outcome labels)",
                       "causal claims (observational strain comparison)"]
    if expr is None:
        cannot.insert(0, "any expression analysis (no expression values in this file; obtain the "
                         "supplementary FPKM/count file)")
    else:
        kind = classify_measurement(expr)["kind"]
        can += ["sample QC, PCA, correlation", "exploratory log2 comparisons between strains"]
        if kind == "raw_counts_like":
            can.append("count-based differential expression")
        else:
            cannot.append("count-based differential expression (values are not raw counts)")
    return {"group_column": group_col, "group_sizes": sizes, "supports": can,
            "does_not_support": cannot}
