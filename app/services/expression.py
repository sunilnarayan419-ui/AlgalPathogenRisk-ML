from __future__ import annotations

import hashlib
import io
import zlib

import numpy as np
import pandas as pd

from app.schemas import ExpressionStats, ExpressionValidationReport, ValidationIssue

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 200 * 1024 * 1024
GZIP_MAGIC = b"\x1f\x8b"


class ExpressionParseError(ValueError):
    """File cannot be interpreted as a tab-separated table."""


class PayloadTooLargeError(ValueError):
    """Compressed or decompressed payload exceeds the configured limit."""


def _maybe_decompress(raw: bytes) -> tuple[bytes, bool]:
    if not raw.startswith(GZIP_MAGIC):
        return raw, False
    decoder = zlib.decompressobj(wbits=31)
    try:
        data = decoder.decompress(raw, MAX_DECOMPRESSED_BYTES + 1)
    except zlib.error as exc:
        raise ExpressionParseError(f"Invalid or corrupt gzip data: {exc}") from exc
    if len(data) > MAX_DECOMPRESSED_BYTES:
        raise PayloadTooLargeError(
            f"Decompressed size exceeds {MAX_DECOMPRESSED_BYTES} bytes."
        )
    if not decoder.eof:
        raise ExpressionParseError("Truncated gzip stream.")
    return data, True


def _parse_table(data: bytes) -> pd.DataFrame:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExpressionParseError("File is not valid UTF-8 text.") from exc
    try:
        # header=None keeps duplicate header names intact so they can be detected.
        table = pd.read_csv(
            io.StringIO(text), sep="\t", header=None, dtype=str, keep_default_na=False
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise ExpressionParseError(f"Could not parse as a tab-separated table: {exc}") from exc
    if table.shape[0] < 2 or table.shape[1] < 2:
        raise ExpressionParseError(
            "Expected a header row, at least one gene row, and at least one sample column."
        )
    return table


def _clean(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _label(value: str, fallback: str) -> str:
    return value if value else fallback


def _cell_examples(
    mask: np.ndarray, gene_ids: pd.Series, sample_ids: pd.Series, limit: int = 5
) -> list[str]:
    examples = []
    for r, c in np.argwhere(mask)[:limit]:
        gene = _label(gene_ids.iloc[int(r)], f"data row {int(r) + 1}")
        sample = _label(sample_ids.iloc[int(c)], f"column {int(c) + 2}")
        examples.append(f"{gene} x {sample}")
    return examples


def _duplicates(ids: pd.Series) -> list[str]:
    nonblank = ids[ids != ""]
    return sorted(set(nonblank[nonblank.duplicated(keep=False)]))


def validate_expression_matrix(raw: bytes) -> ExpressionValidationReport:
    sha256 = hashlib.sha256(raw).hexdigest()
    data, was_gzip = _maybe_decompress(raw)
    table = _parse_table(data)

    header = _clean(table.iloc[0])
    body = table.iloc[1:].reset_index(drop=True)
    gene_ids = _clean(body.iloc[:, 0])
    sample_ids = header.iloc[1:].reset_index(drop=True)
    values = body.iloc[:, 1:].apply(_clean)
    values.columns = range(values.shape[1])

    blank = values.eq("")
    numeric = values.apply(pd.to_numeric, errors="coerce")
    arr = numeric.to_numpy(dtype=float)
    finite = np.isfinite(arr)

    issues: list[ValidationIssue] = []

    def add(code: str, message: str, count: int, examples: list[str]) -> None:
        if count:
            issues.append(ValidationIssue(code=code, message=message, count=count, examples=examples))

    missing_genes = int((gene_ids == "").sum())
    add("missing_gene_ids", "Rows with a missing gene identifier.", missing_genes,
        [f"data row {i + 1}" for i in np.flatnonzero((gene_ids == "").to_numpy())[:5]])
    dup_genes = _duplicates(gene_ids)
    add("duplicate_gene_ids", "Duplicate gene identifiers (count = distinct duplicated IDs).",
        len(dup_genes), dup_genes[:5])

    missing_samples = int((sample_ids == "").sum())
    add("missing_sample_ids", "Columns with a missing sample identifier.", missing_samples,
        [f"column {i + 2}" for i in np.flatnonzero((sample_ids == "").to_numpy())[:5]])
    dup_samples = _duplicates(sample_ids)
    add("duplicate_sample_ids", "Duplicate sample identifiers (count = distinct duplicated IDs).",
        len(dup_samples), dup_samples[:5])

    blank_mask = blank.to_numpy()
    add("missing_values", "Empty expression cells.", int(blank_mask.sum()),
        _cell_examples(blank_mask, gene_ids, sample_ids))

    nonnum_mask = numeric.isna().to_numpy() & ~blank_mask
    add("non_numeric_values", "Cells that are non-numeric (or the text 'NaN').",
        int(nonnum_mask.sum()), _cell_examples(nonnum_mask, gene_ids, sample_ids))

    inf_mask = np.isinf(arr)
    add("non_finite_values", "Infinite expression values.", int(inf_mask.sum()),
        _cell_examples(inf_mask, gene_ids, sample_ids))

    neg_mask = finite & (arr < 0)
    add("negative_values", "Negative expression values (invalid for FPKM/counts).",
        int(neg_mask.sum()), _cell_examples(neg_mask, gene_ids, sample_ids))

    fvals = arr[finite]
    stats = ExpressionStats(
        min=float(fvals.min()) if fvals.size else None,
        max=float(fvals.max()) if fvals.size else None,
        mean=float(fvals.mean()) if fvals.size else None,
        median=float(np.median(fvals)) if fvals.size else None,
        zero_fraction=float((fvals == 0).mean()) if fvals.size else None,
        all_zero_genes=int((arr == 0).all(axis=1).sum()),
    )

    return ExpressionValidationReport(
        valid=not issues,
        sha256=sha256,
        upload_bytes=len(raw),
        decompressed_bytes=len(data),
        was_gzip=was_gzip,
        n_genes=int(body.shape[0]),
        n_samples=int(values.shape[1]),
        gene_id_column_label=header.iloc[0],
        sample_ids=list(sample_ids),
        issues=issues,
        stats=stats,
        orientation_note=(
            "Assumed genes in rows, samples in columns, first column = gene identifier. "
            "Not verified against the source file; confirm before modelling."
        ),
    )
