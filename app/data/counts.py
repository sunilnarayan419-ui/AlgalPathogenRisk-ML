"""Strict raw-count loader and sample-metadata alignment for count-based analyses.

Raw counts (e.g. nf-core/rnaseq ``salmon.merged.gene_counts.tsv`` or featureCounts output)
are required for count-based differential expression. FPKM must NOT be passed here: it is
normalised and non-integer. Genes are rows, samples are columns, first column = gene id.

Not run against the real GSE128981 data (no raw counts were available to the authors).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.data.loader import sha256_file


class CountsValidationError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("Count matrix validation failed: " + "; ".join(issues))
        self.issues = issues


def load_counts(path: str | Path, id_column: int = 0, drop_columns: list[str] | None = None,
                sample_map: dict[str, str] | None = None,
                integer_tolerance: float = 1e-6,
                round_noninteger: bool = False) -> tuple[pd.DataFrame, dict]:
    """Load a raw count TSV(.gz).

    * Negative, non-numeric, infinite, blank, duplicate-ID data are rejected.
    * Non-integer values are rejected unless ``round_noninteger`` is True (needed for
      Salmon/RSEM *estimated* counts; the rounding is recorded in the report).
    * ``sample_map`` renames columns (e.g. SRR run id -> GSM id); unmapped columns are an
      error so that a typo cannot silently drop a sample.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found.")
    try:
        raw = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError, OSError) as exc:
        raise CountsValidationError([f"not a parseable TSV: {exc}"]) from exc
    if raw.shape[0] < 1 or raw.shape[1] < 2:
        raise CountsValidationError(["need >=1 gene row and >=1 sample column"])
    if drop_columns:
        raw = raw.drop(columns=drop_columns, errors="raise")
    ids = raw.iloc[:, id_column].str.strip()
    body = raw.drop(columns=raw.columns[id_column])
    issues: list[str] = []
    if (ids == "").any():
        issues.append(f"{int((ids == '').sum())} blank gene identifiers")
    dup = ids[ids.duplicated(keep=False) & (ids != "")].unique().tolist()
    if dup:
        issues.append(f"{len(dup)} duplicated gene ids (e.g. {dup[:3]})")
    num = body.apply(pd.to_numeric, errors="coerce")
    bad_cols = [c for c in body.columns if num[c].isna().any()]
    if bad_cols:
        issues.append(f"non-numeric/blank values in columns {bad_cols[:5]} "
                      "(annotation column? use drop_columns)")
    arr = num.to_numpy(float)
    if np.isinf(arr).any():
        issues.append("infinite values")
    finite = arr[np.isfinite(arr)]
    if (finite < 0).any():
        issues.append("negative values")
    nonint = np.abs(finite - np.round(finite)) > integer_tolerance
    n_nonint = int(nonint.sum())
    if n_nonint and not round_noninteger:
        issues.append(f"{n_nonint} non-integer values: this looks like normalised data "
                      "(FPKM/TPM) or estimated counts; use raw counts, or set "
                      "round_noninteger for Salmon/RSEM estimated counts")
    if sample_map is not None:
        unmapped = [c for c in body.columns if c not in sample_map]
        if unmapped:
            issues.append(f"columns missing from sample_map: {unmapped[:5]}")
        targets = [sample_map[c] for c in body.columns if c in sample_map]
        if len(set(targets)) != len(targets):
            issues.append("sample_map produces duplicate sample ids")
    if issues:
        raise CountsValidationError(issues)

    df = num.copy()
    if round_noninteger:
        df = df.round()
    df = df.astype("int64")
    if sample_map is not None:
        df = df.rename(columns=sample_map)
    df.index = ids.to_numpy()
    df.index.name = "gene_id"
    lib = df.sum(axis=0)
    report = {"path": str(path), "sha256": sha256_file(path), "n_genes": int(df.shape[0]),
              "n_samples": int(df.shape[1]),
              "library_size_min": int(lib.min()), "library_size_max": int(lib.max()),
              "all_zero_genes": int((df == 0).all(axis=1).sum()),
              "n_noninteger_rounded": n_nonint if round_noninteger else 0,
              "unit": "raw counts (integers)"}
    return df, report


def align_metadata(counts: pd.DataFrame, meta: pd.DataFrame, sample_col: str = "sample_id",
                   required: tuple[str, ...] = ("group",)) -> pd.DataFrame:
    """Return metadata indexed by sample id in the same order as ``counts`` columns.
    Mismatches in either direction are errors; groups are never inferred."""
    missing = [c for c in (sample_col, *required) if c not in meta.columns]
    if missing:
        raise ValueError(f"metadata missing columns {missing}")
    if meta[sample_col].duplicated().any():
        raise ValueError("duplicate sample ids in metadata")
    only_counts = sorted(set(counts.columns) - set(meta[sample_col]))
    only_meta = sorted(set(meta[sample_col]) - set(counts.columns))
    if only_counts or only_meta:
        raise ValueError(f"samples differ: only in counts {only_counts[:5]}, "
                         f"only in metadata {only_meta[:5]}")
    out = meta.set_index(sample_col).loc[list(counts.columns)]
    for c in required:
        if out[c].isna().any() or (out[c].astype(str).str.strip() == "").any():
            raise ValueError(f"metadata column {c!r} has blank values")
    return out
