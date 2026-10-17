"""Strict, pydantic-free FPKM loader for local pipelines (genes in rows, samples in columns).

The real GSE128981 header has not been inspected in this repository's development
environment: use `non_numeric_columns` / `id_column` / `drop_columns` after looking at it.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


class FpkmValidationError(ValueError):
    def __init__(self, issues: list[str]):
        super().__init__("FPKM validation failed: " + "; ".join(issues))
        self.issues = issues


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fpkm(path: str | Path, id_column: int = 0, drop_columns: list[str] | None = None,
              expected_samples: int | None = None) -> tuple[pd.DataFrame, dict]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; see scripts/download_geo.py.")
    if path.suffix == ".gz":
        try:
            with gzip.open(path, "rb") as fh:
                while fh.read(1 << 20):
                    pass
        except (OSError, EOFError) as exc:
            raise FpkmValidationError([f"corrupt gzip: {exc}"]) from exc
    try:
        raw = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise FpkmValidationError([f"not a parseable TSV: {exc}"]) from exc
    if raw.shape[0] < 1 or raw.shape[1] < 2:
        raise FpkmValidationError(["need >=1 gene row and >=1 sample column"])
    if drop_columns:
        raw = raw.drop(columns=drop_columns, errors="raise")
    ids = raw.iloc[:, id_column].str.strip()
    body = raw.drop(columns=raw.columns[id_column])
    issues: list[str] = []
    if (ids == "").any():
        issues.append(f"{int((ids == '').sum())} blank gene identifiers")
    dup_genes = ids[ids.duplicated(keep=False) & (ids != "")].unique().tolist()
    if dup_genes:
        issues.append(f"{len(dup_genes)} duplicated gene ids (e.g. {dup_genes[:3]})")
    dup_cols = [c for c in body.columns if ".1" in c and c.rsplit(".", 1)[0] in body.columns]
    if dup_cols:
        issues.append(f"duplicate sample names renamed by parser: {dup_cols[:3]}")
    num = body.apply(pd.to_numeric, errors="coerce")
    blank = body.apply(lambda c: c.str.strip() == "")
    non_numeric_cols = [c for c in body.columns if num[c].isna().any() and not blank[c].all()]
    if non_numeric_cols:
        issues.append(f"non-numeric/NaN values in columns {non_numeric_cols[:5]} "
                      "(annotation column? use drop_columns)")
    if blank.to_numpy().any():
        issues.append(f"{int(blank.to_numpy().sum())} blank cells")
    arr = num.to_numpy(float)
    if np.isinf(arr).any():
        issues.append("infinite values")
    if (arr[np.isfinite(arr)] < 0).any():
        issues.append("negative values")
    if expected_samples is not None and body.shape[1] != expected_samples:
        issues.append(f"expected {expected_samples} samples, found {body.shape[1]}")
    if issues:
        raise FpkmValidationError(issues)
    df = num.copy()
    df.index = ids.to_numpy()
    df.index.name = "gene_id"
    report = {"path": str(path), "sha256": sha256_file(path), "n_genes": int(df.shape[0]),
              "n_samples": int(df.shape[1]), "all_zero_genes": int((df == 0).all(axis=1).sum()),
              "zero_fraction": float((df.to_numpy() == 0).mean()),
              "orientation": "genes in rows, samples in columns (assumed; confirm)",
              "unit": "FPKM (not counts)"}
    return df, report
